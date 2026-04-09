from node_product import Node


class BinaryTree:
    """Árbol binario que ordena los productos del carrito por precio total."""
    def __init__(self):
        self.raiz = None


    def agregar(self, item):
        """Agrega un producto al árbol, ordenado por precio total."""
        if self.raiz is None:
            self.raiz = Node(item)
        else:
            self._agregar(self.raiz, item)


    def _agregar(self, nodo, item):
        precio_total_item = item['product'].getPriceForCapacity(item['capacity']) * item['quantity']
        precio_total_nodo = nodo.item['product'].getPriceForCapacity(nodo.item['capacity']) * nodo.item['quantity']


        if precio_total_item < precio_total_nodo:
            if nodo.izquierda is None:
                nodo.izquierda = Node(item)
            else:
                self._agregar(nodo.izquierda, item)
        else:
            if nodo.derecha is None:
                nodo.derecha = Node(item)
            else:
                self._agregar(nodo.derecha, item)


    def recorrido_in_order(self):
        """Realiza un recorrido en orden y devuelve una lista de productos ordenados por precio."""
        resultado = []
        self._recorrido_in_order(self.raiz, resultado)
        return resultado


    def _recorrido_in_order(self, nodo, resultado):
        if nodo:
            self._recorrido_in_order(nodo.izquierda, resultado)
            resultado.append(nodo.item)
            self._recorrido_in_order(nodo.derecha, resultado)
