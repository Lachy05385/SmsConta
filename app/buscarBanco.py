
def buscarBancoFaltante(texto):
    
    bpa = ["9205","9206","9238","9212","9245","9248"]
    bandec = ["0689"]
    bancoMetropolitano = ["9227"]
    
    
    if list(filter(lambda x : texto.startswith(x),bpa)):
            texto ="Banco Popular de Ahorro"
    elif list(filter(lambda x : texto.startswith(x),bandec)):
        texto = "Banco de Credito y Comercio..."
    elif list(filter(lambda x : texto.startswith(x),bancoMetropolitano)):
        texto = "Banco Metropilitano..."
    else:
        texto = "Banco Cubano"
        
    return texto

txt = "0689-xxxx-xxxx-9210"

print(buscarBancoFaltante(txt))

