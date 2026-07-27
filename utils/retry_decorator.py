# -*- coding: utf-8 -*-
"""
Decorador para reintentos con backoff exponencial

Uso:
    from utils import con_reintentos
    
    @con_reintentos(max_intentos=3, delay_base=5)
    def mi_funcion_que_puede_fallar():
        # ... código que puede lanzar excepciones
        pass
"""
import time
import logging
import random
from functools import wraps
from typing import Tuple, Type, Callable, Any, Optional

logger = logging.getLogger('VideoAnalyzer')


class ReintentoExhausto(Exception):
    """Excepción cuando se agotan todos los reintentos"""
    def __init__(self, funcion: str, intentos: int, ultimo_error: Exception):
        self.funcion = funcion
        self.intentos = intentos
        self.ultimo_error = ultimo_error
        super().__init__(
            f"Función '{funcion}' falló después de {intentos} intentos. "
            f"Último error: {ultimo_error}"
        )


def con_reintentos(
    max_intentos: int = 3,
    delay_base: float = 5.0,
    delay_max: float = 60.0,
    excepciones: Tuple[Type[Exception], ...] = (Exception,),
    backoff_factor: float = 2.0,
    jitter: bool = True,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
    reraise: bool = True
):
    """
    Decorador para reintentar funciones que pueden fallar
    
    Args:
        max_intentos: Número máximo de intentos (default: 3)
        delay_base: Delay inicial en segundos (default: 5.0)
        delay_max: Delay máximo en segundos (default: 60.0)
        excepciones: Tupla de excepciones a capturar (default: todas)
        backoff_factor: Factor de multiplicación para backoff (default: 2.0)
        jitter: Agregar variación aleatoria al delay (default: True)
        on_retry: Callback llamado en cada reintento (intento, excepcion)
        reraise: Relanzar excepción al agotar reintentos (default: True)
    
    Returns:
        Decorador configurado
    
    Example:
        @con_reintentos(max_intentos=3, delay_base=5)
        def llamar_api():
            response = requests.get("https://api.example.com")
            response.raise_for_status()
            return response.json()
        
        # Con callback personalizado
        def mi_callback(intento, error):
            print(f"Intento {intento} falló: {error}")
        
        @con_reintentos(max_intentos=5, on_retry=mi_callback)
        def otra_funcion():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            ultimo_error = None
            
            for intento in range(1, max_intentos + 1):
                try:
                    return func(*args, **kwargs)
                    
                except excepciones as e:
                    ultimo_error = e
                    
                    # Log del error
                    logger.warning(
                        f"[{func.__name__}] Intento {intento}/{max_intentos} falló: {e}"
                    )
                    
                    # Callback si existe
                    if on_retry:
                        try:
                            on_retry(intento, e)
                        except Exception as callback_error:
                            logger.error(f"Error en callback on_retry: {callback_error}")
                    
                    # Si es el último intento, no esperar
                    if intento == max_intentos:
                        break
                    
                    # Calcular delay con backoff exponencial
                    delay = min(delay_max, delay_base * (backoff_factor ** (intento - 1)))
                    
                    # Agregar jitter para evitar thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.debug(
                        f"[{func.__name__}] Esperando {delay:.1f}s antes del reintento {intento + 1}"
                    )
                    time.sleep(delay)
            
            # Agoté todos los reintentos
            logger.error(
                f"[{func.__name__}] Agotados {max_intentos} reintentos. "
                f"Último error: {ultimo_error}"
            )
            
            if reraise:
                raise ReintentoExhausto(func.__name__, max_intentos, ultimo_error)
            
            return None
        
        return wrapper
    return decorator


def con_reintentos_async(
    max_intentos: int = 3,
    delay_base: float = 5.0,
    delay_max: float = 60.0,
    excepciones: Tuple[Type[Exception], ...] = (Exception,),
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Versión asíncrona del decorador de reintentos
    
    Uso:
        @con_reintentos_async(max_intentos=3)
        async def llamar_api_async():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """
    import asyncio
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            ultimo_error = None
            
            for intento in range(1, max_intentos + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except excepciones as e:
                    ultimo_error = e
                    logger.warning(
                        f"[{func.__name__}] Intento async {intento}/{max_intentos} falló: {e}"
                    )
                    
                    if intento == max_intentos:
                        break
                    
                    delay = min(delay_max, delay_base * (backoff_factor ** (intento - 1)))
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    await asyncio.sleep(delay)
            
            raise ReintentoExhausto(func.__name__, max_intentos, ultimo_error)
        
        return wrapper
    return decorator


# Decoradores preconfigurados para casos comunes
reintentos_api = con_reintentos(
    max_intentos=3,
    delay_base=5,
    excepciones=(ConnectionError, TimeoutError, Exception)
)

reintentos_red = con_reintentos(
    max_intentos=5,
    delay_base=2,
    delay_max=30,
    excepciones=(ConnectionError, TimeoutError, OSError)
)

reintentos_archivo = con_reintentos(
    max_intentos=3,
    delay_base=1,
    excepciones=(IOError, OSError, PermissionError)
)


if __name__ == "__main__":
    # Tests del decorador
    import random
    
    contador = 0
    
    @con_reintentos(max_intentos=3, delay_base=1)
    def funcion_que_falla_a_veces():
        global contador
        contador += 1
        if contador < 3:
            raise ConnectionError(f"Fallo simulado #{contador}")
        return f"¡Éxito en el intento {contador}!"
    
    try:
        resultado = funcion_que_falla_a_veces()
        print(f"Resultado: {resultado}")
    except ReintentoExhausto as e:
        print(f"Falló: {e}")


