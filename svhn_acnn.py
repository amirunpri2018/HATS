from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import cv2
import argparse
import itertools
import functools
import operator

parser = argparse.ArgumentParser()
parser.add_argument("--steps", type=int, default=10000, help="number of training steps")
parser.add_argument("--num_epochs", type=int, default=100, help="number of training epochs")
parser.add_argument("--batch_size", type=int, default=100, help="batch size")
parser.add_argument("--model_dir", type=str, default="svhn_acnn_model", help="model directory")
parser.add_argument('--train', action="store_true", help="with training")
parser.add_argument('--eval', action="store_true", help="with evaluation")
parser.add_argument('--predict', action="store_true", help="with prediction")
parser.add_argument('--gpu', type=str, default="0", help="gpu id")
args = parser.parse_args()

tf.logging.set_verbosity(tf.logging.INFO)


def scale(input, input_min, input_max, output_min, output_max):

    return output_min + (input - input_min) / (input_max - input_min) * (output_max - output_min)


def svhn_input_fn(filenames, training, batch_size, num_epochs):

    def preprocess(image, training):

        image = tf.reshape(image, [64, 64, 3])
        image = tf.random_crop(image, [56, 56, 3])
        image = tf.image.convert_image_dtype(image, tf.float32)

        return image

    def parse(example, training):

        features = tf.parse_single_example(
            serialized=example,
            features={
                "image": tf.FixedLenFeature(
                    shape=[],
                    dtype=tf.string,
                    default_value=""
                ),
                "length": tf.FixedLenFeature(
                    shape=[1],
                    dtype=tf.int64,
                    default_value=[0]
                ),
                "digits": tf.FixedLenFeature(
                    shape=[5],
                    dtype=tf.int64,
                    default_value=[10] * 5
                )
            }
        )

        image = preprocess(tf.decode_raw(features["image"], tf.uint8), training)
        length = tf.cast(features['length'], tf.int32)
        digits = tf.cast(features['digits'], tf.int32)

        return {"images": image}, tf.concat([length, digits], 0)

    dataset = tf.data.TFRecordDataset(filenames)
    dataset = dataset.shuffle(30000)
    dataset = dataset.repeat(num_epochs)
    dataset = dataset.map(functools.partial(parse, training=training))
    dataset = dataset.batch(batch_size)
    dataset = dataset.prefetch(1)

    return dataset.make_one_shot_iterator().get_next()


def svhn_model_fn(features, labels, mode, params):
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    model function for ACNN

    features:   batch of features from input_fn
    labels:     batch of labels from input_fn
    mode:       enum { TRAIN, EVAL, PREDICT }
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    predictions = {}
    predictions.update(features)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 1
    (-1, 64, 64, 1) -> (-1, 64, 64, 64)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = features["images"]

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=64,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 2
    (-1, 64, 64, 64) -> (-1, 64, 64, 64)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=64,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 3
    (-1, 64, 64, 64) -> (-1, 64, 64, 128)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=128,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 4
    (-1, 64, 64, 128) -> (-1, 64, 64, 128)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=128,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 5
    (-1, 64, 64, 128) -> (-1, 64, 64, 256)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=256,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 6
    (-1, 64, 64, 256) -> (-1, 64, 64, 256)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=256,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 7
    (-1, 64, 64, 256) -> (-1, 64, 64, 512)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=512,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 8
    (-1, 64, 64, 512) -> (-1, 64, 64, 512)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=512,
        kernel_size=3,
        strides=1,
        padding="same"
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    attention convolutional layer 1
    (-1, 64, 64, 64) -> (-1, 32, 32, 3)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    attentions = inputs

    attentions = tf.layers.conv2d(
        inputs=attentions,
        filters=3,
        kernel_size=9,
        strides=2,
        padding="same"
    )

    attentions = tf.layers.batch_normalization(
        inputs=attentions,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    attentions = tf.nn.relu(attentions)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    attention convolutional layer 2
    (-1, 32, 32, 3) -> (-1, 16, 16, 3)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    attentions = tf.layers.conv2d(
        inputs=attentions,
        filters=3,
        kernel_size=9,
        strides=2,
        padding="same"
    )

    attentions = tf.layers.batch_normalization(
        inputs=attentions,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    attentions = tf.nn.relu(attentions)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    attention dense layer 3
    (-1, 16, 16, 3) -> (-1, 10)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    shape = attentions.get_shape().as_list()

    attentions = tf.layers.flatten(attentions)

    attentions = tf.layers.dense(
        inputs=attentions,
        units=10
    )

    attentions = tf.layers.batch_normalization(
        inputs=attentions,
        axis=1,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    attentions = tf.nn.relu(attentions)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    attention dense layer 4
    (-1, 10) -> (-1, 16, 16, 3)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    attentions = tf.layers.dense(
        inputs=attentions,
        units=functools.reduce(operator.mul, shape[1:])
    )

    attentions = tf.layers.batch_normalization(
        inputs=attentions,
        axis=1,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    attentions = tf.nn.relu(attentions)

    attentions = tf.reshape(
        tensor=attentions,
        shape=[-1] + shape[1:]
    )

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    attention deconvolutional layer 5
    (-1, 16, 16, 3) -> (-1, 32, 32, 9)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    attentions = tf.layers.conv2d_transpose(
        inputs=attentions,
        filters=9,
        kernel_size=3,
        strides=2,
        padding="same"
    )

    attentions = tf.layers.batch_normalization(
        inputs=attentions,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    attentions = tf.nn.relu(attentions)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    attention deconvolutional layer 6
    (-1, 32, 32, 9) -> (-1, 64, 64, 9)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    attentions = tf.layers.conv2d_transpose(
        inputs=attentions,
        filters=9,
        kernel_size=3,
        strides=2,
        padding="same"
    )

    attentions = tf.layers.batch_normalization(
        inputs=attentions,
        axis=3,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    attentions = tf.nn.sigmoid(attentions)

    predictions["attentions"] = attentions

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    extract layer
    (-1, 64, 64, 512), (-1, 64, 64, 9) -> (-1, 512, 9)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    shape = inputs.get_shape().as_list()

    inputs = tf.reshape(
        tensor=inputs,
        shape=[-1, functools.reduce(operator.mul, shape[1:3]), shape[3]]
    )

    shape = attentions.get_shape().as_list()

    attentions = tf.reshape(
        tensor=attentions,
        shape=[-1, functools.reduce(operator.mul, shape[1:3]), shape[3]]
    )

    inputs = tf.matmul(
        a=inputs,
        b=attentions,
        transpose_a=True,
        transpose_b=False
    )

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    dense layer 9
    (-1, 512, 9) -> (-1, 4096)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.flatten(inputs)

    inputs = tf.layers.dense(
        inputs=inputs,
        units=4096
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=1,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    inputs = tf.layers.dropout(
        inputs=inputs,
        rate=0.4,
        training=mode == tf.estimator.ModeKeys.TRAIN
    )

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    dense layer 10
    (-1, 4096) -> (-1, 4096)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.dense(
        inputs=inputs,
        units=4096
    )

    inputs = tf.layers.batch_normalization(
        inputs=inputs,
        axis=1,
        training=mode == tf.estimator.ModeKeys.TRAIN,
        fused=True
    )

    inputs = tf.nn.relu(inputs)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    logits layer
    (-1, 4096) -> (-1, 6), (-1, 11) * 5
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    multi_logits = [
        tf.layers.dense(
            inputs=inputs,
            units=6
        ),
        tf.layers.dense(
            inputs=inputs,
            units=11
        ),
        tf.layers.dense(
            inputs=inputs,
            units=11
        ),
        tf.layers.dense(
            inputs=inputs,
            units=11
        ),
        tf.layers.dense(
            inputs=inputs,
            units=11
        ),
        tf.layers.dense(
            inputs=inputs,
            units=11
        ),
    ]

    predictions.update({
        "length_classes": tf.stack(
            values=[
                tf.argmax(
                    input=logits,
                    axis=1
                ) for logits in multi_logits[:1]
            ],
            axis=1
        ),
        "digits_classes": tf.stack(
            values=[
                tf.argmax(
                    input=logits,
                    axis=1
                ) for logits in multi_logits[1:]
            ],
            axis=1
        ),
        "length_probabilities": tf.stack(
            values=[
                tf.nn.softmax(
                    logits=logits,
                    dim=1
                ) for logits in multi_logits[:1]
            ],
            axis=1,
            name="length_softmax"
        ),
        "digits_probabilities": tf.stack(
            values=[
                tf.nn.softmax(
                    logits=logits,
                    dim=1
                ) for logits in multi_logits[1:]
            ],
            axis=1,
            name="digits_softmax"
        )
    })

    if mode == tf.estimator.ModeKeys.PREDICT:

        return tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=predictions
        )

    loss = tf.reduce_sum(
        input_tensor=[
            tf.losses.sparse_softmax_cross_entropy(
                labels=labels[:, i],
                logits=logits
            ) for i, logits in enumerate(multi_logits)
        ],
        axis=None
    )

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    IMPORTANT !!!
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    loss += tf.reduce_sum(tf.abs(attentions)) * params["attention_decay"]

    if mode == tf.estimator.ModeKeys.EVAL:

        eval_metric_ops = {
            "accuracy": tf.metrics.accuracy(
                labels=labels,
                predictions=tf.concat(
                    values=[
                        predictions["length_classes"],
                        predictions["digits_classes"]
                    ],
                    axis=1
                )
            )
        }

        return tf.estimator.EstimatorSpec(
            mode=mode,
            loss=loss,
            eval_metric_ops=eval_metric_ops
        )

    if mode == tf.estimator.ModeKeys.TRAIN:

        with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):

            train_op = tf.train.AdamOptimizer().minimize(
                loss=loss,
                global_step=tf.train.get_global_step()
            )

        return tf.estimator.EstimatorSpec(
            mode=mode,
            loss=loss,
            train_op=train_op
        )


def main(unused_argv):

    svhn_classifier = tf.estimator.Estimator(
        model_fn=svhn_model_fn,
        model_dir=args.model_dir,
        config=tf.estimator.RunConfig().replace(
            session_config=tf.ConfigProto(
                gpu_options=tf.GPUOptions(
                    visible_device_list=args.gpu,
                    allow_growth=True
                )
            )
        ),
        params={
            "attention_decay": 1e-6
        }
    )

    if args.train:

        train_input_fn = functools.partial(
            svhn_input_fn,
            filenames=["data/train.tfrecords"],
            training=True,
            batch_size=args.batch_size,
            num_epochs=args.num_epochs
        )

        logging_hook = tf.train.LoggingTensorHook(
            tensors={
                "length_probabilities": "length_softmax",
                "digits_probabilities": "digits_softmax"
            },
            every_n_iter=100
        )

        svhn_classifier.train(
            input_fn=train_input_fn,
            hooks=[logging_hook]
        )

    if args.eval:

        eval_input_fn = functools.partial(
            svhn_input_fn,
            filenames=["data/test.tfrecords"],
            training=False,
            batch_size=args.batch_size,
            num_epochs=1
        )

        eval_results = svhn_classifier.evaluate(
            input_fn=eval_input_fn
        )

        print(eval_results)

    if args.predict:

        predict_input_fn = functools.partial(
            svhn_input_fn,
            filenames=["data/test.tfrecords"],
            training=False,
            batch_size=args.batch_size,
            num_epochs=1
        )

        predict_results = svhn_classifier.predict(
            input_fn=predict_input_fn
        )

        figure = plt.figure()
        artists = []

        for predict_result in itertools.islice(predict_results, 10):

            attention = predict_result["attentions"]
            attention = scale(attention, attention.min(), attention.max(), 0, 1)
            attention = np.apply_along_axis(np.sum, axis=-1, arr=attention)
            attention = cv2.resize(attention, (56, 56))

            image = predict_result["images"]
            image[:, :, 0] += attention

            artists.append([plt.imshow(image, animated=True)])

        ani = animation.ArtistAnimation(figure, artists, interval=1000, repeat=True)
        anim.save("svhn_attention.gif", writer="imagemagick")


if __name__ == "__main__":
    tf.app.run()
