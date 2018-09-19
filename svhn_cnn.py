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
parser.add_argument("--model_dir", type=str, default="svhn_cnn_model", help="model directory")
parser.add_argument('--train', action="store_true", help="with training")
parser.add_argument('--eval', action="store_true", help="with evaluation")
parser.add_argument('--predict', action="store_true", help="with prediction")
parser.add_argument('--gpu', type=str, default="0", help="gpu id")
args = parser.parse_args()

tf.logging.set_verbosity(tf.logging.INFO)


def svhn_input_fn(filenames, batch_size, num_epochs):

    def parse(example):

        features = tf.parse_single_example(
            serialized=example,
            features={
                "image": tf.FixedLenFeature(
                    shape=[],
                    dtype=tf.string,
                    default_value=""
                ),
                "label": tf.FixedLenFeature(
                    shape=[5],
                    dtype=tf.int64,
                    default_value=[10] * 5
                )
            }
        )

        image = tf.decode_raw(features["image"], tf.uint8)
        image = tf.image.convert_image_dtype(image, tf.float32)
        image = tf.reshape(image, [128, 128, 3])

        label = tf.cast(features["label"], tf.int32)

        return {"images": image}, label

    dataset = tf.data.TFRecordDataset(filenames)
    dataset = dataset.shuffle(30000)
    dataset = dataset.repeat(num_epochs)
    dataset = dataset.map(parse)
    dataset = dataset.batch(batch_size)
    dataset = dataset.prefetch(1)

    return dataset.make_one_shot_iterator().get_next()


def cnn_model_fn(features, labels, mode, params):
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    model function for CNN

    features:   batch of features from input_fn
    labels:     batch of labels from input_fn
    mode:       enum { TRAIN, EVAL, PREDICT }
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    predictions = {}
    predictions.update(features)

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 1
    (-1, 128, 128, 3) -> (-1, 64, 64, 32)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = features["images"]

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=32,
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

    inputs = tf.layers.conv2d(
        inputs=inputs,
        filters=32,
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

    inputs = tf.layers.max_pooling2d(
        inputs=inputs,
        pool_size=2,
        strides=2,
        padding="same"
    )

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    convolutional layer 2
    (-1, 64, 64, 32) -> (-1, 32, 32, 64)
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

    inputs = tf.layers.max_pooling2d(
        inputs=inputs,
        pool_size=2,
        strides=2,
        padding="same"
    )

    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""
    dense layer 3
    (-1, 32, 32, 64) -> (-1, 1024)
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    inputs = tf.layers.flatten(inputs)

    inputs = tf.layers.dense(
        inputs=inputs,
        units=1024
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
    (-1, 1024) -> (-1, 11) * 5
    """""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    multi_logits = tf.stack(
        values=[
            tf.layers.dense(
                inputs=inputs,
                units=11
            ) for i in range(5)
        ],
        axis=1
    )

    predictions.update({
        "classes": tf.argmax(
            input=multi_logits,
            axis=-1
        ),
        "softmax": tf.nn.softmax(
            logits=multi_logits,
            dim=-1,
            name="softmax"
        )
    })

    if mode == tf.estimator.ModeKeys.PREDICT:

        return tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=predictions
        )

    loss = tf.reduce_mean(
        input_tensor=[
            tf.losses.sparse_softmax_cross_entropy(
                labels=labels[:, i],
                logits=multi_logits[:, i, :]
            ) for i in range(5)
        ],
        axis=None
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

    if mode == tf.estimator.ModeKeys.EVAL:

        eval_metric_ops = {
            "accuracy": tf.metrics.accuracy(
                labels=labels,
                predictions=predictions["classes"]
            )
        }

        return tf.estimator.EstimatorSpec(
            mode=mode,
            loss=loss,
            eval_metric_ops=eval_metric_ops
        )


def main(unused_argv):

    svhn_classifier = tf.estimator.Estimator(
        model_fn=cnn_model_fn,
        model_dir=args.model_dir,
        config=tf.estimator.RunConfig().replace(
            session_config=tf.ConfigProto(
                gpu_options=tf.GPUOptions(
                    visible_device_list=args.gpu,
                    allow_growth=True
                )
            )
        ),
        params={}
    )

    if args.train:

        train_input_fn = functools.partial(
            svhn_input_fn,
            filenames=["data/svhn/train.tfrecords"],
            batch_size=args.batch_size,
            num_epochs=args.num_epochs
        )

        logging_hook = tf.train.LoggingTensorHook(
            tensors={
                "softmax": "softmax"
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
            filenames=["data/svhn/test.tfrecords"],
            batch_size=args.batch_size,
            num_epochs=1
        )

        eval_results = svhn_classifier.evaluate(
            input_fn=eval_input_fn
        )

        print(eval_results)


if __name__ == "__main__":
    tf.app.run()
