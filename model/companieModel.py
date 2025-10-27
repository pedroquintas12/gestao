
import base64
import gzip
from config.db import db
from model.mixins import TimestampMixin

class companie(db.Model,TimestampMixin):

    __tablename__ = "companie"

    id_companie = db.Column(db.Integer, primary_key= True, autoincrement=True)
    nome = db.Column(db.String(150), nullable= False)
    cnpj = db.Column(db.String(30), nullable = True)
    endereco = db.Column(db.String(100), nullable= True)
    numero = db.Column(db.String(30), nullable= True)
    imagem_bloob = db.Column(db.Text, nullable= True)
    imagem_mime = db.Column(db.String(50), nullable= True)
    deleted = db.Column(db.Integer, nullable=False, default=False)


    @staticmethod
    def _is_gzip(data: bytes) -> bool:
        # assinatura do gzip: 1f 8b
        return isinstance(data, (bytes, bytearray)) and len(data) >= 2 and data[:2] == b'\x1f\x8b'

    def set_photo_bytes(self, raw_bytes: bytes, mime: str | None = None, compresslevel: int = 6):
        """
        Salva foto compactada com gzip em foto_bloob.
        - raw_bytes: bytes originais do arquivo (jpg/png)
        - mime: 'image/jpeg' | 'image/png' 
        """
        if not raw_bytes:
            self.imagem_bloob = None
            self.imagem_mime = None
            return
        # sempre compacta; (nota: jpeg/png já são comprimidos, mas gzip ajuda mais)
        self.imagem_bloob = gzip.compress(raw_bytes, compresslevel=compresslevel)
        # guarda mime para montar o data URL corretamente
        self.imagem_mime = (mime or self.imagem_mime or 'image/jpeg')[:50]
        
    def get_photo_bytes(self) -> bytes | None:
            """
            Retorna bytes descompactados da foto (ou None).
            Aguenta dados antigos não-gzip (backward compatibility).
            """
            if not self.imagem_bloob:
                return None
            data = bytes(self.imagem_bloob)
            if self._is_gzip(data):
                try:
                    return gzip.decompress(data)
                except Exception:
                    # se estiver corrompido, retorna como está
                    return data
            # dados legados sem gzip
            return data
    @property
    def photo(self) -> str | None:
        """
        Data URL para o front (<img src="...">). Descompacta na hora.
        Se não houver foto, retorna None (o JS usa placeholder).
        """
        raw = self.get_photo_bytes()
        if not raw:
            return None
        mime = self.imagem_mime or 'image/jpeg'
        b64 = base64.b64encode(raw).decode('utf-8')
        return f"data:{mime};base64,{b64}"
    
    def to_dict(self):
        return {
            "id_companie": self.id_companie,
            "nome": self.nome,
            "cnpj": self.cnpj,
            "endereco": self.endereco,
            "numero": self.numero,
            "logo": self.photo
        }