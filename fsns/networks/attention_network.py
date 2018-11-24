import tensorflow as tf
import numpy as np
from sequential.algorithms import *


class AttentionNetwork(object):

    def __init__(self, conv_params, deconv_params, rnn_params, data_format):

        self.conv_params = conv_params
        self.deconv_params = deconv_params
        self.rnn_params = rnn_params
        self.data_format = data_format

    def __call__(self, inputs, training, name="attention_network", reuse=None):

        with tf.variable_scope(name, reuse=reuse):

            for i, conv_param in enumerate(self.conv_params):

                with tf.variable_scope("conv_block_{}".format(i)):

                    inputs = map_innermost(
                        function=compose(
                            lambda inputs: tf.layers.conv2d(
                                inputs=inputs,
                                filters=conv_param.filters,
                                kernel_size=conv_param.kernel_size,
                                strides=conv_param.strides,
                                padding="same",
                                data_format=self.data_format,
                                use_bias=False,
                                kernel_initializer=tf.variance_scaling_initializer(
                                    scale=2.0,
                                    mode="fan_in",
                                    distribution="normal",
                                ),
                                name="conv2d",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.layers.batch_normalization(
                                inputs=inputs,
                                axis=1 if self.data_format == "channels_first" else 3,
                                training=training,
                                fused=True,
                                name="batch_normalization",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.nn.relu(inputs)
                        ),
                        sequence=inputs
                    )

            shape = inputs.shape.as_list()

            inputs = map_innermost(
                function=lambda inputs: tf.layers.flatten(inputs),
                sequence=inputs
            )

            for i, rnn_param in enumerate(self.rnn_params):

                with tf.variable_scope("rnn_block_{}".format(i)):

                    multi_cell = tf.nn.rnn_cell.MultiRNNCell([
                        tf.nn.rnn_cell.LSTMCell(
                            num_units=num_units,
                            use_peepholes=True
                        ) for num_units in rnn_param.num_units
                    ])

                    inputs = map_innermost(
                        function=lambda inputs: tf.nn.static_rnn(
                            cell=multi_cell,
                            inputs=[inputs] * rnn_param.sequence_length,
                            dtype=tf.float32,
                            scope="rnn"
                        )[0],
                        sequence=inputs
                    )

            inputs = map_innermost(
                function=lambda inputs: tf.reshape(inputs, [-1] + shape[1:]),
                sequence=inputs
            )

            '''
            with tf.variable_scope("projection_block"):

                inputs = map_innermost(
                    function=compose(
                        lambda inputs: tf.layers.dense(
                            inputs=inputs,
                            units=np.prod(shape[1:]),
                            kernel_initializer=tf.variance_scaling_initializer(
                                scale=2.0,
                                mode="fan_in",
                                distribution="normal",
                            ),
                            bias_initializer=tf.zeros_initializer(),
                            name="projection",
                            reuse=tf.AUTO_REUSE
                        ),
                        lambda inputs: tf.nn.relu(inputs),
                        lambda inputs: tf.reshape(
                            tensor=inputs,
                            shape=[-1] + shape[1:]
                        )
                    ),
                    sequence=inputs
                )
            '''

            for i, deconv_param in enumerate(self.deconv_params[:-1]):

                with tf.variable_scope("deconv_block_{}".format(i)):

                    inputs = map_innermost(
                        function=compose(
                            lambda inputs: tf.layers.conv2d_transpose(
                                inputs=inputs,
                                filters=deconv_param.filters,
                                kernel_size=deconv_param.kernel_size,
                                strides=deconv_param.strides,
                                padding="same",
                                data_format=self.data_format,
                                use_bias=False,
                                kernel_initializer=tf.variance_scaling_initializer(
                                    scale=2.0,
                                    mode="fan_in",
                                    distribution="normal",
                                ),
                                name="deconv2d",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.layers.batch_normalization(
                                inputs=inputs,
                                axis=1 if self.data_format == "channels_first" else 3,
                                training=training,
                                fused=True,
                                name="batch_normalization",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.nn.relu(inputs)
                        ),
                        sequence=inputs
                    )

            for i, deconv_param in enumerate(self.deconv_params[-1:], i + 1):

                with tf.variable_scope("deconv_block_{}".format(i)):

                    inputs = map_innermost(
                        function=compose(
                            lambda inputs: tf.layers.conv2d_transpose(
                                inputs=inputs,
                                filters=deconv_param.filters,
                                kernel_size=deconv_param.kernel_size,
                                strides=deconv_param.strides,
                                padding="same",
                                data_format=self.data_format,
                                use_bias=False,
                                kernel_initializer=tf.variance_scaling_initializer(
                                    scale=1.0,
                                    mode="fan_avg",
                                    distribution="normal",
                                ),
                                name="deconv2d",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.layers.batch_normalization(
                                inputs=inputs,
                                axis=1 if self.data_format == "channels_first" else 3,
                                training=training,
                                fused=True,
                                name="batch_normalization",
                                reuse=tf.AUTO_REUSE
                            ),
                            lambda inputs: tf.nn.sigmoid(inputs)
                        ),
                        sequence=inputs
                    )

            return inputs
