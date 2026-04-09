class Node:
    """Clase para representar un nodo en el árbol binario del carrito."""
    def __init__(self, item):
        self.item = item  # El producto en el carrito
        self.izquierda = None
        self.derecha = None
