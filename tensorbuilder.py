"""
# Tensor Builder

TensorBuilder is light wrapper over TensorFlow that enables you to easily create complex deep neural networks using the Builder Pattern through a functional [fluent](https://en.wikipedia.org/wiki/Fluent_interface) [immutable](https://en.wikipedia.org/wiki/Immutable_object) API. The main goals of TensorBuilder are

* Be a light-weight wrapper around TensorFlow fully compatible with its functions.
* Let the user name and inspect the tensorflow Variables generated by TensorBuilder
* Enable the user to creatingeate complex branched topologies while maintaining a fluent API (see [Builder.branch](http://cgarciae.github.io/tensorbuilder/tensorbuilder.m.html#tensorbuilder.tensorbuilder.Builder.branch))

TensorBuilder has a small set of primitives that enable you to express complex networks while maintaining a consistent API. Its branching mechanism enables you to express through the structure of your code the structure of the network, even when you have complex sub-branching expansions and reductions, all this while keeping the same fluid API.

TensorBuilder takes inspiration from [prettytensor](https://github.com/google/prettytensor) but its internals are simpler, its API is smaller but equally powerfull, its branching mechanism is more expresive and doesn't break the fluent API, and its immutable nature helps avoid most a lot of conceptual complexity.

## Installation

At the moment the easiest way to install it in your project is to do the following

1. `cd` to your project
2. `git clone https://github.com/cgarciae/tensorbuilder.git`
3. Erase the .git file/folder`rm tensorbuilder/.git` or `rm -fr tensorbuilder/.git`

## Getting Started

Create neural network with a [5, 10, 3] architecture with a `softmax` output layer and a `tanh` hidden layer through a Builder and then get back its tensor:

    import tensorflow as tf
    import tensorbuilder as tb

    x = tf.placeholder(tf.float32, shape=[None, 5])

    h = (
        x.builder()
        .connect_layer(10, fn=tf.nn.tanh)
        .connect_layer(3, fn=tf.nn.softmax)
        .tensor
    )

## Branching
If you are sufficiently familiar with tensorflow or use prettytensor then you might appreciate the branching capabilities of Tensor Builder in this (overly complex) example

    import tensorflow as tf
    import tensorbuilder as tb

    x = tf.placeholder(tf.float32, shape=[None, 5])
    keep_prob = tf.placeholder(tf.float32)

    h = (
        x.builder()
        .connect_layer(10)
        .branch(lambda root:
        [
            root
            .connect_layer(3, fn=tf.nn.relu)
        ,
            root
            .connect_layer(9, fn=tf.nn.tanh)
            .branch(lambda root2: 
            [
              root2
              .connect_layer(6, fn=tf.nn.sigmoid)
            ,
              root2
              .map(tf.nn.dropout, keep_prob)
              .connect_layer(8, tf.nn.softmax)
            ])
        ])
        .connect_layer(6, fn=tf.nn.sigmoid)
        .tensor
    )

## Documentation

The main documentaion is in the [tensorbuilder module](http://cgarciae.github.io/tensorbuilder/tensorbuilder.m.html). The documentation for the complete project is [here](http://cgarciae.github.io/tensorbuilder/).

## Examples

Here are the examples for each method of the API. If you are understand all examples, then you've understood the complete API.


"""

__version__ = "0.0.1"

import tensorflow as tf
import numpy as np
import functools
from decorator import decorator


# Decorators
@decorator
def _immutable(method, self, *args, **kwargs):
    """
    Decorator. Passes a copy of the entity to the method so that the original object remains un touched.
    Used in methods to get a fluent immatable API.
    """
    return method(self.copy(), *args, **kwargs)



class Builder(object):
    """
    The Builder class is a wrapper around a Tensor. Most of its method are immutable in the sense that they don't modify the caller object but rather always make a copy, they also tend to return a Builder so you you can keep fluently chaining methods.
    
    To create a builder from a method you have these options:

    1. Use the `tensorbuilder.tensorbuilder.builder` function
    
            tb.builder(tensor)

    2. Use the monkey-patched method on the Tensor class

            tensor.builder()
    
    """
    def __init__(self, tensor, variables={}):
        super(Builder, self).__init__()
        
        self.tensor = tensor
        """A `tensorflow` Tensor."""

        self.variables = variables
        """A dictionary that accumulates the **tf.Variable** tensors generated during the building process, it has the form {tensor_name: String -> tensor: tf.Variable}. Since functions like `tensorbuilder.tensorbuilder.Builder.connect_layer` hides you the complexity of creating the **bias** and **weights** of your network, `tensorbuilder.tensorbuilder.Builder` stores them in this field. The methods of this class enables you to set the names of these variables, but take into account that the final name is actually the name of the tensor, with is set by `tensorflow`. Check their documentation to see how the name is defined."""

    def copy(self):
        """Returns a copy of this Builder"""
        return Builder(self.tensor, self.variables.copy())

    @_immutable
    def connect_weights(builder, size, name=None, weights_name=None):
        """
        `@_immutable`

        Let **x** be `tensorbuilder.tensorbuilder.Builder.tensor` of shape **[m, n]**, and let **w** be a **tf.Variable** of shape **[n, size]**. Then `builder.connect_weights(size)` computes `tf.matmul(x, w)`. 

        The returned `tensorbuilder.tensorbuilder.Builder` has **w** stored inside `tensorbuilder.tensorbuilder.Builder.variables`.

        **Parameters**
        
        * `size`: an `int` representing the size of the layer (number of neurons)
        * `name`: the name of the tensor (default: "connect_weights")
        * `weights_name`: the name of the **w** tensor of type `tf.Variable`.

        **Return**

        * `tensorbuilder.tensorbuilder.Builder`
        
        **Examples**

        The following builds `tf.matmul(x, w)`

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])

            z = x.builder().connect_weights(3, weights_name="weights") 
        """

        m = int(builder.tensor.get_shape()[1])
        n = size

        w = tf.Variable(tf.random_uniform([m, n], -1.0, 1.0), name=weights_name)
        var_name = weights_name if weights_name else w.name

        builder.variables[var_name] = w
        builder.tensor = tf.matmul(builder.tensor, w, name=name)

        return builder

    @_immutable
    def connect_bias(builder, name=None, bias_name=None):
        """
        `@_immutable`

        Let **x** be `tensorbuilder.tensorbuilder.Builder.tensor` of shape **[m, n]**, and let **b** be a **tf.Variable** of shape **[n]**. Then `builder.connect_bias()` computes `tf.add(x, b)`.

        The returned `tensorbuilder.tensorbuilder.Builder` has **b** stored inside `tensorbuilder.tensorbuilder.Builder.variables`.

        **Parameters**
        
        * `name`: the name of the tensor (default: "connect_bias")
        * `bias_name`: the name of the `w` tensor of type `tf.Variable` (default: "b").

        **Return**

        * `tensorbuilder.tensorbuilder.Builder`
        
        **Examples**
        
        The following builds `tf.matmul(x, w) + b`

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])

            z = (
                x.builder()
                .connect_weights(3, weights_name="weights")
                .connect_bias(bias_name="bias")
            )

        Note, the previous is equivalent to using `tensorbuilder.tensorbuilder.Builder.connect_layer` like this

            z = (
                x.builder()
                .connect_layer(3, weights_name="weights", bias_name="bias")
            )
        """
        m = int(builder.tensor.get_shape()[1])

        b = tf.Variable(tf.random_uniform([m], -1.0, 1.0), name=bias_name)
        var_name = bias_name if bias_name else b.name

        builder.variables[var_name] = b
        builder.tensor = tf.add(builder.tensor, b, name=name)

        return builder


    @_immutable
    def connect_layer(builder, size, fn=None, name=None, weights_name=None, bias=True, bias_name=None):
        """
        `@_immutable`

        Let **x** be `tensorbuilder.tensorbuilder.Builder.tensor` of shape **[m, n]**, let **w** be a **tf.Variable** of shape **[n, size]**, let **b** be a **tf.Variable** of shape **[n]**, and **fn** be a function from a tensor to a tensor. Then `builder.connect_layer(size, fn=fn)` computes `fn(tf.matmul(x, w) + b)`. If **fn** is not present the layer is linear.

        Note that **fn** must expose the keyword/named argument `name`, this is compatible with the tensorflow API.

        The returned `tensorbuilder.tensorbuilder.Builder` has **b** and **w** stored inside `tensorbuilder.tensorbuilder.Builder.variables`.

        **Parameters**
        
        * `fn`: a function of type `tensor -> tensor`. If `fn` is `None` then its not applied, resulting in just a linear trasformation. (default: None)
        * `size`: an `int` representing the size of the layer (number of neurons)
        * `name`: the name of the tensor (default: `"layer"`)
        * `bias`: determines where to use a bias **b** or not (default: `True`)
        * `weights_name`: the name of the `w` tensor of type `tf.Variable` (default: `None`)
        * `bias_name`: the name of the `w` tensor of type `tf.Variable` (default: `None`)

        **Return**

        * `tensorbuilder.tensorbuilder.Builder`
        
        **Examples**

        The following builds the computation `tf.nn.sigmoid(tf.matmul(x, w) + b)`
            
            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])
            
            h = (
                x.builder()
                .connect_layer(3, fn=tf.nn.sigmoid)
            )

        The previous is equivalent to using 
        
            h = (
                x.builder()
                .connect_weights(3)
                .connect_bias()
                .map(tf.nn.sigmoid)
            )

        You can chain various `connect_layer`s to get deeper neural networks

            import tensorflow as tf
            import tensorbuilder as tb
        
            x = tf.placeholder(tf.float32, shape=[None, 40])

            h = (
                x.builder()
                .connect_layer(100, fn=tf.nn.tanh)
                .connect_layer(30, fn=tf.nn.softmax)
            )
        """


        builder = builder.connect_weights(size, weights_name=weights_name)

        if bias:
            builder = builder.connect_bias(bias_name=bias_name)

        if fn:
            builder.tensor = fn(builder.tensor, name=name)

        return builder

    @_immutable
    def map(builder, fn, *args, **kwargs):
        """
        `@_immutable`

        Let **x** be `tensorbuilder.tensorbuilder.Builder.tensor` and **fn** be a function from a tensor to a tensor. Then `builder.map(fn)` computes `fn(x)`. All extra positional and named arguments are forwarded to **fn** such that

            builder.map(fn, arg1, arg2, ..., kwarg1=kwarg1, kwarg2=kwarg2, ...)

        internally results in

            builder.tensor = fn(builder.tensor, arg1, arg2, ..., kwarg1=kwarg1, kwarg2=kwarg2, ...)

        **Parameters**
        
        * `fn`: a function of type `tensor -> tensor`.

        **Return**

        * `tensorbuilder.tensorbuilder.Builder`
        
        **Examples**
        
        The following constructs a neural network with the architecture `[40 input, 100 tanh, 30 softmax]` and and applies `dropout` to the tanh layer

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 40])
            keep_prob = tf.placeholder(tf.float32)

            h = (
                x.builder()
                .connect_layer(100, fn=tf.nn.tanh)
                .map(tb.nn.dropout, keep_prob)
                .connect_layer(30, fn=tf.nn.softmax)
            )

        """
        builder.tensor = fn(builder.tensor, *args, **kwargs)
        return builder

    @_immutable
    def then(builder, fn):
        """
        `@_immutable`

        Expects a function **fn** with type `builder -> builder`. This method is used primarily to manupilate the Builder with very fine grain control through the fluent immutable API.

        **Parameters**
        
        * `fn`: a function of type `builder -> builder`.

        **Return**

        * `tensorbuilder.tensorbuilder.Builder`
        
        ** Example **

        The following *manually* constructs the computation `tf.nn.sigmoid(tf.matmul(x, w) + b)` while updating the `tensorbuilder.tensorbuiler.Builder.variables` dictionary.

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 40])
            keep_prob = tf.placeholder(tf.float32)

            def sigmoid_layer(builder, size):
                m = int(builder.tensor.get_shape()[1])
                n = size

                w = tf.Variable(tf.random_uniform([m, n], -1.0, 1.0))
                b = tf.Variable(tf.random_uniform([n], -1.0, 1.0))

                builder.variables[w.name] = w
                builder.variables[b.name] = b

                builder.tensor = tf.nn.sigmoid(tf.matmul(builder.tensor, w) + b)

                return builder

            h = (
                x.builder()
                .then(lambda builder: sigmoid_layer(builder, 3))
            )

        Note that the previous if equivalent to

            h = (
                x.builder()
                .connect_layer(3, fn=tf.nn.sigmoid)
            )

        """
        return fn(builder)

    @_immutable
    def branch(builder, fn):
        """
        `@_immutable`

        Expects a function **fn** with type `Builder -> list( Builder | BuilderTree )`. This method enables you to *branch* the computational graph so you can easily create neural networks with more complex topologies. You can later 

        **Parameters**
        
        * `fn`: a function of type `Builder -> list( Builder | BuilderTree )`.

        **Return**

        * `tensorbuilder.tensorbuilder.BuilderTree`
        
        ** Example **

        The following will create a sigmoid layer but will branch the computation at the logit (z) so you get both the output tensor `h` and `trainer` tensor. Observe that first the logit `z` is calculated by creating a linear layer with `connect_layer(1)` and then its branched out

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])
            y = tf.placeholder(tf.float32, shape=[None, 1])

            [h, trainer] = (
                x.builder()
                .connect_layer(1)
                .branch(lambda z:
                [
                    z.map(tf.nn.sigmoid)
                ,
                    z.map(tf.nn.sigmoid_cross_entropy_with_logits, y)
                    .map(tf.train.AdamOptimizer(0.01).minimize)
                ])
                .tensors()
            )

        Note that you have to use the `tensorbuilder.tensorbuilder.BuilderTree.tensors` method from the `tensorbuilder.tensorbuilder.BuilderTree` class to get the tensors back. Remember that you can also contain `tensorbuilder.tensorbuilder.BuilderTree` elements when you branch out, this means that you can keep branching inside branch. Don't worry that the tree keep getting deeper, `tensorbuilder.tensorbuilder.BuilderTree` has methods that help you flatten or reduce the tree. 
        
        The following example will show you how create a (overly) complex tree and then connect all the leaf nodes to a single `sigmoid` layer

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])
            keep_prob = tf.placeholder(tf.float32)

            h = (
                x.builder()
                .connect_layer(10)
                .branch(lambda base:
                [
                    base
                    .connect_layer(3, fn=tf.nn.relu)
                ,
                    base
                    .connect_layer(9, fn=tf.nn.tanh)
                    .branch(lambda base2: 
                    [
                        base2
                        .connect_layer(6, fn=tf.nn.sigmoid)
                    ,
                        base2
                        .map(tf.nn.dropout, keep_prob)
                        .connect_layer(8, tf.nn.softmax)
                    ])
                ])
                .connect_layer(6, fn=tf.nn.sigmoid)
            )

        ** See Also **

        * `tensorbuilder.tensorbuilder.BuilderTree`
        * `tensorbuilder.tensorbuilder.BuilderTree.connect_layer`
        * `tensorbuilder.tensorbuilder.BuilderTree.builders`
        * `tensorbuilder.tensorbuilder.BuilderTree.tensors`

        """
        branches = fn(builder)
        return BuilderTree(branches)

    @_immutable
    def _leafs(builder):
        """A generator function that yields the builder, used by `tensorbuilder.tensorbuilder.BuilderTree.leafs` of `tensorbuilder.tensorbuilder.BuilderTree`"""
        yield builder


class BuilderTree(object):
    """
    BuilderTree is a class that enable you to perform computations over a complex branched builder. It contains methods to get all the leaf `tensorbuilder.tensorbuilder.Builder` nodes, connect all the leaf nodes to a single layer, etc.
    """
    def __init__(self, branches):
        super(BuilderTree, self).__init__()
        self.branches = branches
        """
        A list that can contain elements that are of type `tensorbuilder.tensorbuilder.Builder` or `tensorbuilder.tensorbuilder.BuilderTree`. 
        """

    def copy(self):
        branches = self.branches[:]
        return BuilderTree(branches)

    def builders(self):
        """
        Returns a flattened list `tensorbuilder.tensorbuilder.Builder`s contained by this tree. The whole result is flattened in case of sub-elements are also `tensorbuilder.tensorbuilder.BuilderTree`s.

        **Return**

        * `list( tensorbuilder.tensorbuilder.Builder )`
        
        ** Example **

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])
            y = tf.placeholder(tf.float32, shape=[None, 1])

            [h_builder, trainer_builder] = (
                x.builder()
                .connect_layer(1)
                .branch(lambda z:
                [
                    z.map(tf.nn.sigmoid)
                ,
                    z.map(tf.nn.sigmoid_cross_entropy_with_logits, y)
                    .map(tf.train.AdamOptimizer(0.01).minimize)
                ])
                .builders()
            )

        """
        return [builder for builder in self._leafs() ]

    def tensors(self):
        """
        Same as `tensorbuilder.tensorbuilder.BuilderTree.builders` but extracts the tensor from each `tensorbuilder.tensorbuilder.Builder`.

        **Return**

        * `list( tf.Tensor )`
        
        ** Example **

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])
            y = tf.placeholder(tf.float32, shape=[None, 1])

            [h_tensor, trainer_tensor] = (
                x.builder()
                .connect_layer(1)
                .branch(lambda z:
                [
                    z.map(tf.nn.sigmoid)
                ,
                    z.map(tf.nn.sigmoid_cross_entropy_with_logits, y)
                    .map(tf.train.AdamOptimizer(0.01).minimize)
                ])
                .tensors()
            )
        """
        return [builder.tensor for builder in self._leafs() ]

    @_immutable
    def connect_layer(tree, size, fn=None, name="layer", bias=True, bias_name=None):
        """
        Connects all the leaf `tensorbuilder.tensorbuilder.Builder` nodes of this tree to a single layer. The order of computation is done as follows

        1. Each leaf builder node is linearly connected to a layer of size `size` with no bias.
        2. All these layers of size `size` are added together (reduced with +)
        3. If `bias` is `True` then a bias added
        4. If `fn` is not `None` then the function `fn` is mapped

        ** Parameters **

        * `fn`: a function of type `tensor -> tensor`. If `fn` is `None` then its not applied, resulting in just a linear trasformation. (default: None)
        * `name`: the name of the tensor (default: `"layer"`)
        * `bias`: determines where to use a bias **b** or not (default: `True`)
        * `bias_name`: the name of the `w` tensor of type `tf.Variable` (default: `None`)
        
        ** Examples **

        # The following example shows you how to connect two tensors (rather builders) of different shapes to a single `softmax` layer of shape [None, 3]

            import tensorflow as tf
            import tensorbuilder as tb

            a = tf.placeholder(tf.float32, shape=[None, 8]).builder()
            b = tf.placeholder(tf.float32, shape=[None, 5]).builder()

            h = (
                tb.branches([a, b])
                .connect_layer(3, fn=tf.nn.softmax)
            )

        The next example show you how you can use this to pass the input layer directly through one branch, and "analyze" it with a `tanh layer` filter through the other, both of these are connect to a single `softmax` output layer

            import tensorflow as tf
            import tensorbuilder as tb

            x = tf.placeholder(tf.float32, shape=[None, 5])

            h = (
                x.builder()
                .branch(lambda x: 
                [
                    x
                ,
                    x.connect_layer(10, fn=tf.nn.tanh)
                ])
                .connect_layer(3, fn=tf.nn.softmax)
            )
        """
        builders = [ builder.connect_weights(size) for builder in tree._leafs() ]
        builder = _add_builders(builders)

        if bias:
            builder = builder.connect_bias(bias_name=bias_name)

        if fn:
            builder.tensor = fn(builder.tensor, name=name)

        return builder


    @_immutable
    def _leafs(tree):
        """A generator function that lazily returns all the Builders contianed by this tree"""
        for branch in tree.branches:
            for builder in branch._leafs():
                yield builder




## Module Funs
def builder(tensor):
    """
    Takes a tensor and returns a `tensorbuilder.tensorbuilder.Builder` that contians it. If function is also used to monkey-patch tensorflow's Tensor class with a method of the same name.

    ** Parameters **

    * `tensor`: a tensorflow Tensor
    
    #### Example

    The following example shows you how to construct a `tensorbuilder.tensorbuilder.Builder` from a tensorflow Tensor.

        import tensorflow as tf
        import tensorbuilder as tb

        a = tf.placeholder(tf.float32, shape=[None, 8])
        a_builder = tb.builder(a)

    The previous is the same as

        a_builder = tf.placeholder(tf.float32, shape=[None, 8]).builder()

    since tensorbuilder monkey-patches tensorflow's Tensor with this function as method.
    """
    return Builder(tensor)

def branches(builder_list):
    """
    Takes a list with elements of type `tensorbuilder.tensorbuilder.Builder` or `tensorbuilder.tensorbuilder.BuilderTree` and returns a `tensorbuilder.tensorbuilder.BuilderTree`

    ** Parameters **

    * `builder_list`: list of type `list( Builder | BuilderTree)`
    
    #### Example

    Given a list of Builders and/or BuilderTrees you construct a `tensorbuilder.tensorbuilder.BuilderTree` like this

        import tensorflow as tf
        import tensorbuilder as tb

        a = tf.placeholder(tf.float32, shape=[None, 8]).builder()
        b = tf.placeholder(tf.float32, shape=[None, 8]).builder()

        tree = tb.branches([a, b])

    `tensorbuilder.tensorbuilder.BuilderTree`s are usually constructed using `tensorbuilder.tensorbuilder.Builder.branch` of the `tensorbuilder.tensorbuilder.Builder` class, but you can use this for special cases

    """
    return BuilderTree(builder_list)

def _add_builders(builders):
    tensor = None
    variables = {}

    for builder in builders:
        if tensor == None:
            tensor = builder.tensor
        else:
            tensor += builder.tensor

        variables.update(builder.variables)

    return Builder(tensor, variables=variables)
