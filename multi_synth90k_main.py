# =============================================================
# dataset details
# dataset: multi synth90k
# download: made by make_multi_synth90k.cpp
# train: 800000
# val: 100000
# test: 100000
# max num chars: 10
# classes: [0-9A-Z](case-insensitive)
# word accuracy: 0.863 (100000 steps)
# edit distance: 0.033 (100000 steps)
# =============================================================

import tensorflow as tf
import argparse
from attrdict import AttrDict
from dataset import Dataset
from models.hats import HATS
from networks.attention_network import AttentionNetwork
from networks.pyramid_resnet import PyramidResNet
from algorithms import *

parser = argparse.ArgumentParser()
parser.add_argument("--model_dir", type=str, default="multi_synth90k_hats", help="model directory")
parser.add_argument("--pretrained_model_dir", type=str, default="", help="pretrained model directory")
parser.add_argument('--filenames', type=str, nargs="+", default=["multi_synth90k_train.tfrecord"], help="tfrecord filenames")
parser.add_argument("--num_epochs", type=int, default=10, help="number of training epochs")
parser.add_argument("--batch_size", type=int, default=16, help="batch size")
parser.add_argument("--data_format", type=str, default="channels_first", help="data format")
parser.add_argument("--steps", type=int, default=None, help="number of training epochs")
parser.add_argument("--max_steps", type=int, default=None, help="maximum number of training epochs")
parser.add_argument("--train", action="store_true", help="with training")
parser.add_argument("--eval", action="store_true", help="with evaluation")
parser.add_argument("--predict", action="store_true", help="with prediction")
parser.add_argument("--gpu", type=str, default="0,1,2", help="gpu id")
parser.add_argument("--random_seed", type=int, default=1209, help="random seed")
args = parser.parse_args()

tf.logging.set_verbosity(tf.logging.INFO)


def main(unused_argv):

    classifier = tf.estimator.Estimator(
        model_fn=lambda features, labels, mode: HATS(
            backbone_network=PyramidResNet(
                conv_param=AttrDict(filters=64, kernel_size=[7, 7], strides=[2, 2]),
                pool_param=AttrDict(pool_size=[3, 3], strides=[2, 2]),
                residual_params=[
                    AttrDict(filters=64, strides=[1, 1], blocks=2),
                    AttrDict(filters=128, strides=[2, 2], blocks=2),
                    AttrDict(filters=256, strides=[2, 2], blocks=2),
                    AttrDict(filters=512, strides=[2, 2], blocks=2),
                ],
                data_format=args.data_format,
                pretrained_model_dir=args.pretrained_model_dir,
                pretrained_model_scope="pyramid_resnet"
            ),
            attention_network=AttentionNetwork(
                conv_params=[
                    AttrDict(filters=16, kernel_size=[3, 3], strides=[2, 2]),
                    AttrDict(filters=16, kernel_size=[3, 3], strides=[2, 2]),
                ],
                deconv_params=[
                    AttrDict(filters=16, kernel_size=[3, 3], strides=[2, 2]),
                    AttrDict(filters=16, kernel_size=[3, 3], strides=[2, 2]),
                ],
                rnn_params=[
                    AttrDict(sequence_length=5, units=256),
                    AttrDict(sequence_length=10, units=256),
                ],
                data_format=args.data_format
            ),
            num_classes=37,
            data_format=args.data_format,
            hyper_params=AttrDict(
                attention_decay=1e-5,
                learning_rate=0.001,
                beta1=0.9,
                beta2=0.999
            )
        )(features, labels, mode),
        model_dir=args.model_dir,
        config=tf.estimator.RunConfig(
            tf_random_seed=args.random_seed,
            session_config=tf.ConfigProto(
                gpu_options=tf.GPUOptions(
                    visible_device_list=args.gpu,
                    allow_growth=True
                )
            )
        )
    )

    if args.train:

        classifier.train(
            input_fn=Dataset(
                filenames=args.filenames,
                num_epochs=args.num_epochs,
                batch_size=args.batch_size,
                sequence_lengths=[5, 10],
                image_size=[256, 256],
                data_format=args.data_format,
                encoding="jpeg"
            ),
            steps=args.steps,
            max_steps=args.max_steps
        )

    if args.eval:

        eval_results = classifier.evaluate(
            input_fn=Dataset(
                filenames=args.filenames,
                num_epochs=1,
                batch_size=args.batch_size,
                sequence_lengths=[5, 10],
                image_size=[256, 256],
                data_format=args.data_format,
                encoding="jpeg"
            )
        )

        print(eval_results)

    if args.predict:

        import cv2
        import itertools

        predict_results = classifier.predict(
            input_fn=Dataset(
                filenames=args.filenames,
                num_epochs=1,
                batch_size=args.batch_size,
                sequence_lengths=[5, 10],
                image_size=[256, 256],
                data_format=args.data_format,
                encoding="jpeg"
            )
        )

        for i, predict_result in enumerate(itertools.islice(predict_results, 100)):

            image = predict_result["images"]
            attention_maps = predict_result["attention_maps"]

            if args.data_format == "channels_first":
                image = np.transpose(image, [1, 2, 0])
                attention_maps = np.transpose(attention_maps, [0, 1, 3, 4, 2])

            for attention_maps_ in attention_maps:

                for attention_map in attention_maps_:

                    attention_map = (attention_map - attention_map.min()) / (attention_map.max() - attention_map.min())
                    attention_map[attention_map < 0.5] = 0.0
                    attention_map = cv2.resize(attention_map, image.shape[:-1])
                    image[:, :, -1] += attention_map

            cv2.imwrite("outputs/multi_synth90k/attention_map_{}.jpg".format(i), image * 255.)


if __name__ == "__main__":
    tf.app.run()
