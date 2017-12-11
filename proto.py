# script version to build a graph and test on compute stick
import tensorflow as tf
import numpy as np

# params
batch_size = 1
x_size = 5000
y_size = 1
z_size = 1

out_size = 1

T = 100

neurons_first_layer = 10

learning_rate = 1e-2

# example data
ex_input = np.random.rand(x_size,y_size,z_size,T)
ex_output = np.sum(np.exp(ex_input**5),0)
ex_output = ex_output / np.linalg.norm(ex_output)

# input & target
input_ = tf.placeholder(dtype=tf.float32, shape=[x_size, y_size, z_size], name="input")
target = tf.placeholder(dtype=tf.float32, shape=[1, out_size], name="target")
transformed_input = tf.reshape(input_, [1, x_size], name="transformed_input")

# one MLP layer
W_first = tf.get_variable("weights1", [x_size, neurons_first_layer], dtype=tf.float32)
linear_first = tf.matmul(transformed_input, W_first)
transform_first = tf.nn.relu(linear_first)

# perceptron output
W_second = tf.get_variable("weights2", [neurons_first_layer, 1], dtype=tf.float32)
linear_second = tf.matmul(transform_first, W_second)
output = tf.nn.tanh(linear_second, name="output")

# loss, gradient and optimizer
loss = tf.losses.mean_squared_error(target, output)

tvars = tf.trainable_variables()
grads = tf.gradients(loss, tvars)
optimizer = tf.train.GradientDescentOptimizer(learning_rate)

train_op = optimizer.apply_gradients(zip(grads, tvars))

saver = tf.train.Saver()

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())

    for t in range(T):
        feed_dict = {input_: ex_input[:,:,:,t], target: ex_output[:,:,t]}
        out, _ = sess.run([output,train_op], feed_dict)
        print( "Target: {} and Prediction: {}".format(ex_output[:,:,t], out))

    saver.save(sess, "tmp/model.ckpt")
