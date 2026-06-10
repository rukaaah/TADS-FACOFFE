"""
Módulo: retry.py
Descrição: Centraliza a lógica do Padrão de Retentativa (Retry Pattern).
Contém decoradores de resiliência que protegem operações críticas de rede 
(como salvar no banco de dados ou ler do RabbitMQ) contra falhas temporárias 
(ex: picos de I/O, perda momentânea de conexão), usando backoff exponencial.
"""

import logging
import time
from typing import Callable, TypeVar, Any, Tuple, Type
from functools import wraps
from random import uniform

logger = logging.getLogger(__name__)

# TypeVar para permitir type hints genéricos no decorador
F = TypeVar('F', bound=Callable[..., Any])


class RetryConfig:
    """Configuração centralizada para o padrão de retentativa."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        backoff_multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        """
        Inicializa a configuração de retry.
        
        Args:
            max_attempts: Número máximo de tentativas (padrão: 3)
            initial_delay: Delay inicial em segundos (padrão: 1.0s)
            backoff_multiplier: Multiplicador exponencial (padrão: 2.0x)
            max_delay: Delay máximo em segundos (padrão: 60.0s)
            jitter: Adiciona variação aleatória para evitar thundering herd (padrão: True)
            exceptions: Tupla de exceções a serem capturadas (padrão: Exception)
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_multiplier = backoff_multiplier
        self.max_delay = max_delay
        self.jitter = jitter
        self.exceptions = exceptions

    def calculate_delay(self, attempt: int) -> float:
        """
        Calcula o delay para uma tentativa específica com backoff exponencial.
        
        Args:
            attempt: Número da tentativa (começando em 0)
            
        Returns:
            Tempo de espera em segundos
        """
        # Backoff exponencial: initial_delay * (backoff_multiplier ^ attempt)
        delay = self.initial_delay * (self.backoff_multiplier ** attempt)
        
        # Garante que não ultrapasse o delay máximo
        delay = min(delay, self.max_delay)
        
        # Adiciona jitter (variação aleatória entre 0 e 100% do delay)
        if self.jitter:
            delay = delay * uniform(0.5, 1.0)
        
        return delay


def retry(config: RetryConfig = None) -> Callable[[F], F]:
    """
    Decorador de resiliência com retry automático e backoff exponencial.
    
    Protege operações críticas de rede contra falhas temporárias, tentando
    novamente com delays exponenciais crescentes.
    
    Args:
        config: Instância de RetryConfig com as configurações desejadas.
                Se None, usa configurações padrão.
    
    Returns:
        Decorador que envolve a função com lógica de retry.
    
    Exemplo:
        # Retry com configuração padrão
        @retry()
        def save_to_database(data):
            # Operação crítica
            pass
        
        # Retry com configuração customizada
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            backoff_multiplier=2.0,
            exceptions=(ConnectionError, TimeoutError)
        )
        
        @retry(config)
        def connect_to_rabbitmq():
            # Operação de conexão
            pass
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    logger.debug(
                        f"[RETRY] Tentativa {attempt + 1}/{config.max_attempts} "
                        f"para {func.__name__}"
                    )
                    return func(*args, **kwargs)
                
                except config.exceptions as e:
                    last_exception = e
                    
                    # Se foi a última tentativa, levanta a exceção
                    if attempt == config.max_attempts - 1:
                        logger.error(
                            f"[RETRY] Falha permanente em {func.__name__} após "
                            f"{config.max_attempts} tentativas: {str(e)}"
                        )
                        raise
                    
                    # Calcula o delay para a próxima tentativa
                    delay = config.calculate_delay(attempt)
                    logger.warning(
                        f"[RETRY] {func.__name__} falhou (tentativa {attempt + 1}/"
                        f"{config.max_attempts}): {str(e)}. "
                        f"Retentando em {delay:.2f}s..."
                    )
                    
                    # Aguarda antes de tentar novamente
                    time.sleep(delay)
            
            # Esta linha nunca deveria ser alcançada, mas garante type safety
            if last_exception:
                raise last_exception
        
        return wrapper  # type: ignore
    
    return decorator



# CONFIGURAÇÕES PRÉ-DEFINIDAS PARA CASOS DE USO COMUNS

# Para operações de banco de dados (salvamento, atualização, etc.)
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    backoff_multiplier=2.0,
    max_delay=30.0,
    jitter=True,
    exceptions=(Exception,)
)

# Para operações de mensageria (leitura/escrita em RabbitMQ)
MESSAGING_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    backoff_multiplier=2.0,
    max_delay=60.0,
    jitter=True,
    exceptions=(Exception,)
)

# Para operações de rede genéricas (chamadas HTTP, DNS, etc.)
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    initial_delay=0.3,
    backoff_multiplier=2.0,
    max_delay=30.0,
    jitter=True,
    exceptions=(Exception,)
)