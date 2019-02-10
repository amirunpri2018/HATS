# =============================================================
# dataset details
# dataset: synth90k
# download: http://www.robots.ox.ac.uk/~vgg/data/text/
# train: 7224612
# val: 802734
# test: 891927
# max num chars: 23
# classes: [0-9A-Z](case-insensitive)
# word accuracy:
# edit distance:
# pretrained model: chars74k classifier
# max steps: 100000 batch size: 128
# =============================================================

import tensorflow as tf
import optuna
import argparse
from attrdict import AttrDict
from dataset import Dataset
from models.hats import HATS
from networks.attention_network import AttentionNetwork
from networks.pyramid_resnet import PyramidResNet
from algorithms import *

parser = argparse.ArgumentParser()
parser.add_argument("--model_dir", type=str, default="synth90k_hats", help="model directory")
parser.add_argument("--pretrained_model_dir", type=str, default="", help="pretrained model directory")
parser.add_argument('--train_filenames', type=str, nargs="+", default=["synth90k_train.tfrecord"], help="tfrecords for training")
parser.add_argument('--test_filenames', type=str, nargs="+", default=["synth90k_test.tfrecord"], help="tfrecords for test")
parser.add_argument("--num_epochs", type=int, default=None, help="number of training epochs")
parser.add_argument("--batch_size", type=int, default=100, help="batch size")
parser.add_argument("--random_seed", type=int, default=1209, help="random seed")
parser.add_argument("--data_format", type=str, default="channels_first", help="data format")
parser.add_argument("--max_steps", type=int, default=100000, help="maximum number of training steps")
parser.add_argument("--gpu", type=str, default="0,1,2", help="gpu id")
args = parser.parse_args()

tf.logging.set_verbosity(tf.logging.INFO)


def objective(trial):

    learning_rate = trial.suggest_loguniform("learning_rate", 1e-3, 1e-0)
    learning_rate = trial.suggest_int("decay_steps", args.max_steps // 10, args.max_steps)

    estimator = tf.estimator.Estimator(
        model_fn=lambda features, labels, mode: HATS(
            backbone_network=PyramidResNet(
                conv_param=AttrDict(filters=64, kernel_size=[7, 7], strides=[2, 2]),
                pool_param=None,
                residual_params=[
                    AttrDict(filters=64, strides=[2, 2], blocks=2),
                    AttrDict(filters=128, strides=[2, 2], blocks=2),
                    AttrDict(filters=256, strides=[2, 2], blocks=2),
                    AttrDict(filters=512, strides=[2, 2], blocks=2),
                ],
                data_format=args.data_format
            ),
            attention_network=AttentionNetwork(
                conv_params=[
                    AttrDict(filters=8, kernel_size=[3, 3], strides=[2, 2]),
                    AttrDict(filters=8, kernel_size=[3, 3], strides=[2, 2]),
                ],
                rnn_params=[
                    AttrDict(sequence_length=23, units=256),
                ],
                deconv_params=[
                    AttrDict(filters=8, kernel_size=[3, 3], strides=[2, 2]),
                    AttrDict(filters=8, kernel_size=[3, 3], strides=[2, 2]),
                ],
                data_format=args.data_format
            ),
            num_classes=37,
            data_format=args.data_format,
            hyper_params=AttrDict(
                weight_decay=1e-4,
                attention_decay_fn=lambda global_step: tf.train.cosine_decay(
                    learning_rate=1e-6,
                    global_step=global_step,
                    decay_steps=args.max_steps
                ),
                learning_rate_fn=lambda global_steps: tf.train.exponential_decay(
                    learning_rate=learning_rate,
                    global_step=global_step,
                    decay_steps=decay_steps,
                    decay_rate=0.1,
                    staircase=False,
                    name=None
                ),
                momentum=0.9
            )
        )(features, labels, mode),
        model_dir="{}_(lr={}, ds={})".format(
            args.model_dir,
            learning_rate,
            decay_steps
        ),
        config=tf.estimator.RunConfig(
            tf_random_seed=args.random_seed,
            save_summary_steps=args.max_steps // 1000,
            save_checkpoints_steps=args.max_steps // 1000,
            session_config=tf.ConfigProto(
                gpu_options=tf.GPUOptions(
                    visible_device_list=args.gpu,
                    allow_growth=True
                )
            )
        ),
        warm_start_from=tf.estimator.WarmStartSettings(
            ckpt_to_initialize_from=args.pretrained_model_dir,
            vars_to_warm_start=".*pyramid_resnet.*"
        )
    )

    train_input_fn = Dataset(
        filenames=args.train_filenames,
        num_epochs=args.num_epochs,
        batch_size=args.batch_size,
        random_seed=args.random_seed,
        sequence_lengths=[23],
        image_size=[256, 256],
        data_format=args.data_format,
        encoding="jpeg"
    )

    eval_input_fn = Dataset(
        filenames=args.test_filenames,
        num_epochs=1,
        batch_size=args.batch_size,
        random_seed=args.random_seed,
        sequence_lengths=[23],
        image_size=[256, 256],
        data_format=args.data_format,
        encoding="jpeg"
    )

    optuna_pruning_hook = optuna.integration.TensorFlowPruningHook(
        trial=trial,
        estimator=estimator,
        metric="word_accuracy",
        is_higher_better=True,
        run_every_steps=args.max_steps // 100
    )

    estimator.train(
        input_fn=train_input_fn,
        max_steps=args.max_steps,
        hooks=[optuna_pruning_hook]
    )

    eval_result = AttrDict(estimator.evaluate(
        input_fn=eval_input_fn,
        steps=sum([
            len(list(tf.io.tf_record_iterator(filename)))
            for filename in args.test_filenames
        ]) // args.batch_size // 10
    ))

    return 1.0 - eval_result.word_accuracy


if __name__ == "__main__":

    study = optuna.create_study(
        pruner=optuna.pruners.MedianPruner(
            n_startup_trials=10,
            n_warmup_steps=args.max_steps // 10
        )
    )

    study.optimize(objective, n_trials=100)

    print(study.best_trial)
    print([t.state for t in study.trials])
