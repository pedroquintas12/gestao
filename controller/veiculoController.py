from flask import request
from service.veiculoService import veiculoService

class veiculoController:

    def create():
        data =request.get_json(silent= True)
        app = veiculoService.create_veiculo(data)
        return app