import tensorflow as tf

cell1 = tf.nn.rnn_cell.LSTMCell(10)
cell2 = tf.nn.rnn_cell.LSTMCell(10)

x = tf.zeros([10, 10])

y1 = tf.nn.static_rnn(cell1, [x], dtype=tf.float32, scope="a")
y2 = tf.nn.static_rnn(cell2, [x], dtype=tf.float32, scope="b")
y3 = tf.nn.static_rnn(cell2, [x], dtype=tf.float32, scope="b")

with tf.Session() as sess:

    print(tf.trainable_variables())

    sess.run(tf.global_variables_initializer())

    sess.run([y1, y2])