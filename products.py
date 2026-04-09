from abc import ABC, abstractmethod

# Clases base de productos
class BaseProduct(ABC):
    """Clase abstracta que define la estructura base de un producto."""
    def __init__(self, id, name, brand, scent, duration, price, imageUrl):
        self.id = id
        self.name = name
        self.brand = brand
        self.scent = scent
        self.duration = duration
        self.price = price
        self.imageUrl = imageUrl
        self.selected_capacity = 50  # Capacidad por defecto


    @abstractmethod
    def getName(self):
        pass


    @abstractmethod
    def getBrand(self):
        pass


    @abstractmethod
    def getScent(self):
        pass


    @abstractmethod
    def getDuration(self):
        pass


    @abstractmethod
    def getPrice(self):
        pass


    @abstractmethod
    def getImageUrl(self):
        pass


    def setSelectedCapacity(self, capacity):
        """Actualiza la capacidad seleccionada y calcula el nuevo precio."""
        self.selected_capacity = capacity


    def getSelectedCapacity(self):
        """Devuelve la capacidad seleccionada."""
        return self.selected_capacity


    def getPriceForCapacity(self, capacity):
        """Devuelve el precio basado en una capacidad específica."""
        if capacity == 50:
            return self.price
        elif capacity == 70:
            return self.price * 1.15
        elif capacity == 100:
            return self.price * 1.45
        return self.price

    def tipoFiltro(self, filtro):
        """Aplica uno o varios filtros (brand, scent, duration)."""
        for clave, valor in filtro.items():
            if clave == 'brand' and self.getBrand() != valor:
                return False
            elif clave == 'scent' and self.getScent() != valor:
                return False
            elif clave == 'duration' and self.getDuration() != valor:
                return False
        return True



# Clases concretas de productos
class Product(BaseProduct):
    def getName(self):
        return self.name


    def getBrand(self):
        return self.brand


    def getScent(self):
        return self.scent


    def getDuration(self):
        return self.duration


    def getPrice(self):
        return self.price


    def getImageUrl(self):
        return self.imageUrl



class DiscountedProduct(BaseProduct):
    def __init__(self, id, name, brand, scent, duration, price, imageUrl, discount):
        super().__init__(id, name, brand, scent, duration, price, imageUrl)
        self.discount = discount

    def getName(self):
        return self.name


    def getBrand(self):
        return self.brand


    def getScent(self):
        return self.scent


    def getDuration(self):
        return self.duration


    def getPrice(self):
        return self.price * (1 - (self.discount / 100))


    def getPriceForCapacity(self, capacity):
        """Devuelve el precio con descuento basado en la capacidad específica."""
        basePrice = super().getPriceForCapacity(capacity)
        return basePrice * (1 - (self.discount / 100))


    def getImageUrl(self):
        return self.imageUrl

