import tensorflow as tf
import numpy as np
from . import ops
from . import rnn
from algorithms import *
from itertools import *


class AttentionNetwork(object):

    def __init__(self, conv_params, rnn_params, deconv_params, data_format):

        self.conv_params = conv_params
        self.rnn_params = rnn_params
        self.deconv_params = deconv_params
        self.data_format = data_format

    def __call__(self, inputs, labels, training, name="attention_network", reuse=None):

        with tf.variable_scope(name, reuse=reuse):

            for i, conv_param in enumerate(self.conv_params):

                with tf.variable_scope("conv_block_{}".format(i)):

                    inputs = compose(
                        lambda inputs: tf.layers.conv2d(
                            inputs=inputs,
                            filters=conv_param.filters,
                            kernel_size=conv_param.kernel_size,
                            strides=conv_param.strides,
                            padding="same",
                            data_format=self.data_format,
                            use_bias=False,
                            kernel_initializer=tf.initializers.variance_scaling(
                                scale=2.0,
                                mode="fan_in",
                                distribution="untruncated_normal"
                            ),
                            name="conv2d",
                            reuse=None
                        ),
                        lambda inputs: ops.batch_normalization(
                            inputs=inputs,
                            data_format=self.data_format,
                            training=training,
                            name="batch_normalization",
                            reuse=None
                        ),
                        lambda inputs: tf.nn.relu(inputs)
                    )(inputs)

            image_shape = inputs.shape

            feature_maps = map_innermost_element(
                func=lambda inputs: tf.layers.flatten(inputs),
                seq=inputs
            )

            labels = tf.expand_dims(labels, axis=-1)

            def get_seq_lens(labels, indices):

                classes = labels.shape[-1]
                labels = tf.slice(labels, [0] + indices, [-1] + [1] * len(indices))

                return tf.count_nonzero(tf.reduce_any(
                    input_tensor=tf.not_equal(labels, classes - 1),
                    axis=range(2, len(labels.shape))
                ), axis=1)

            for i, rnn_param in enumerate(self.rnn_params):

                with tf.variable_scope("rnn_block_{}".format(i)):

                    lstm_cell = tf.nn.rnn_cell.LSTMCell(
                        num_units=rnn_param.num_units,
                        use_peepholes=False,
                        activation=tf.nn.tanh,
                        initializer=tf.initializers.variance_scaling(
                            scale=1.0,
                            mode="fan_avg",
                            distribution="untruncated_normal"
                        )
                    )

                    inputs = map_innermost_element(
                        func=lambda indices_inputs: rnn.static_rnn(
                            cell=lstm_cell,
                            inputs=[feature_maps] * rnn_param.max_seq_len,
                            initial_state=(
                                indices_inputs[1] if indices_inputs[1] else
                                lstm_cell.zero_state(
                                    batch_size=tf.shape(feature_maps)[0],
                                    dtype=tf.float32
                                )
                            ),
                            sequence_length=get_seq_lens(
                                labels=labels,
                                indices=indices_inputs[0]
                            )
                        ),
                        seq=enumerate_innermost_element(inputs)
                    )

            with tf.variable_scope("projection_block"):

                inputs = map_innermost_element(
                    function=lambda inputs: tf.layers.dense(
                        inputs=inputs.h,
                        units=np.prod(image_shape[1:]),
                        activation=tf.nn.relu,
                        kernel_initializer=tf.initializers.variance_scaling(
                            scale=2.0,
                            mode="fan_in",
                            distribution="untruncated_normal"
                        ),
                        bias_initializer=tf.zeros_initializer(),
                        name="dense",
                        reuse=tf.AUTO_REUSE
                    ),
                    sequence=inputs
                )

            inputs = map_innermost_element(
                func=lambda inputs: tf.reshape(inputs, [-1] + image_shape[1:]),
                seq=inputs
            )

            for i, deconv_param in enumerate(self.deconv_params[:-1]):

                with tf.variable_scope("deconv_block_{}".format(i)):

                    inputs = map_innermost_element(
                        func=compose(
                            lambda inputs: tf.layers.conv2d_transpose(
                                inputs=inputs,
                                filters=deconv_param.filters,
                                kernel_size=deconv_param.kernel_size,
                                strides=deconv_param.strides,
                                padding="same",
                                data_format=self.data_format,
                                use_bias=False,
                                kernel_initializer=tf.initializers.variance_scaling(
                                    scale=2.0,
                                    mode="fan_in",
                                    distribution="untruncated_normal"
                                ),
                                name="deconv2d",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: ops.batch_normalization(
                                inputs=inputs,
                                data_format=self.data_format,
                                training=training,
                                name="batch_normalization",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.nn.relu(inputs)
                        ),
                        seq=inputs
                    )

            for i, deconv_param in enumerate(self.deconv_params[-1:], i + 1):

                with tf.variable_scope("deconv_block_{}".format(i)):

                    inputs = map_innermost_element(
                        func=compose(
                            lambda inputs: tf.layers.conv2d_transpose(
                                inputs=inputs,
                                filters=deconv_param.filters,
                                kernel_size=deconv_param.kernel_size,
                                strides=deconv_param.strides,
                                padding="same",
                                data_format=self.data_format,
                                use_bias=False,
                                kernel_initializer=tf.initializers.variance_scaling(
                                    scale=1.0,
                                    mode="fan_avg",
                                    distribution="untruncated_normal"
                                ),
                                name="deconv2d",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: ops.batch_normalization(
                                inputs=inputs,
                                data_format=self.data_format,
                                training=training,
                                name="batch_normalization",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.nn.sigmoid(inputs)
                        ),
                        seq=inputs
                    )

            return inputs