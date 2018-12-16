import tensorflow as tf
import numpy as np
import functools
import glob
import os
from algorithms import *


class Dataset(object):

    def __init__(self, filenames, num_epochs, batch_size, buffer_size,
                 image_size, channels_first, sequence_lengths):

        self.dataset = tf.data.TFRecordDataset(filenames)
        self.dataset = self.dataset.shuffle(
            buffer_size=buffer_size,
            reshuffle_each_iteration=True
        )
        self.dataset = self.dataset.repeat(num_epochs)
        self.dataset = self.dataset.map(
            map_func=functools.partial(
                self.parse,
                image_size=image_size,
                channels_first=channels_first,
                sequence_lengths=sequence_lengths
            ),
            num_parallel_calls=os.cpu_count()
        )
        self.dataset = self.dataset.batch(batch_size)
        self.dataset = self.dataset.prefetch(1)
        self.iterator = self.dataset.make_one_shot_iterator()

    def parse(self, example, image_size, channels_first, sequence_lengths):

        features = tf.parse_single_example(
            serialized=example,
            features={
                "path": tf.FixedLenFeature(
                    shape=[],
                    dtype=tf.string
                ),
                "label": tf.FixedLenFeature(
                    shape=[np.prod(sequence_lengths)],
                    dtype=tf.int64
                )
            }
        )

        image = tf.read_file(features["path"])
        image = tf.image.decode_jpeg(image, 3)
        image = tf.image.convert_image_dtype(image, tf.float32)

        if image_size:
            image = tf.image.resize_images(image, image_size)

        if channels_first:
            image = tf.transpose(image, [2, 0, 1])

        label = tf.cast(features["label"], tf.int32)
        label = tf.reshape(label, sequence_lengths)

        return {"image": image}, label

    def get_next(self):

        return self.iterator.get_next()


def convert_dataset(input_directory, output_filename, sequence_lengths):

    with tf.python_io.TFRecordWriter(output_filename) as writer:

        class_ids = {}
        class_ids.update({chr(j): i for i, j in enumerate(range(ord("0"), ord("9") + 1), 0)})
        class_ids.update({chr(j): i for i, j in enumerate(range(ord("A"), ord("Z") + 1), class_ids["9"] + 1)})
        class_ids.update({chr(j): i for i, j in enumerate(range(ord("a"), ord("z") + 1), class_ids["Z"] + 1)}),
        class_ids.update({"": max(class_ids.values()) + 1})

        for input_filename in glob.glob(os.path.join(input_directory, "*")):

            label = os.path.splitext(os.path.basename(input_filename))[0].split("_")[1:]
            label = map_innermost_element(list, label)

            for i, sequence_length in enumerate(sequence_lengths[::-1]):

                label = map_innermost_list(
                    function=lambda sequence: np.pad(
                        array=sequence,
                        pad_width=[[0, sequence_length - len(sequence)]] + [[0, 0]] * i,
                        mode="constant",
                        constant_values=""
                    ),
                    sequence=label
                )

            label = map_innermost_element(lambda char: class_ids[char], label)

            writer.write(
                record=tf.train.Example(
                    features=tf.train.Features(
                        feature={
                            "path": tf.train.Feature(
                                bytes_list=tf.train.BytesList(
                                    value=[input_filename.encode("utf-8")]
                                )
                            ),
                            "label": tf.train.Feature(
                                int64_list=tf.train.Int64List(
                                    value=label.astype(np.int32).reshape([-1]).tolist()
                                )
                            )
                        }
                    )
                ).SerializeToString()
            )
