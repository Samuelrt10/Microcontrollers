import tensorflow as tf
from tensorflow.keras import layers, models

# 1. Cargar el dataset oficial MNIST (números escritos a mano del 0 al 9)
mnist = tf.keras.datasets.mnist
(x_train, y_train), (x_test, y_test) = mnist.load_data()

# 2. Preprocesar los datos (normalizar píxeles para que estén entre 0 y 1)
x_train, x_test = x_train / 255.0, x_test / 255.0

# Expandir dimensiones para que la CNN los entienda como imágenes con 1 canal de color (grises)
x_train = x_train[..., tf.newaxis]
x_test = x_test[..., tf.newaxis]

# 3. Construir la arquitectura de la Red Neuronal Convolucional (CNN)
modelo = models.Sequential([
    layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Flatten(),
    layers.Dense(64, activation='relu'),
    layers.Dense(10, activation='softmax') # 10 salidas (dígitos del 0 al 9)
])

# 4. Compilar el modelo
modelo.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])

# 5. Entrenar el modelo (5 épocas son suficientes para lograr >98% de precisión)
print("Iniciando el entrenamiento de la red neuronal...")
modelo.fit(x_train, y_train, epochs=5, validation_data=(x_test, y_test))

# 6. Guardar el modelo en el formato requerido
modelo.save('mnist_model.h5')
print("¡Modelo guardado exitosamente como 'mnist_model.h5' en tu carpeta!")