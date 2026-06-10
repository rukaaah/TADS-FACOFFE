"""
Módulo: retry.py
Descrição: Centraliza a lógica do Padrão de Retentativa (Retry Pattern).
Contém decoradores de resiliência que protegem operações críticas de rede 
(como salvar no banco de dados ou ler do RabbitMQ) contra falhas temporárias 
(ex: picos de I/O, perda momentânea de conexão), usando backoff exponencial.
Utiliza Tenacity para suporte nativo a funções síncronas e assíncronas.
"""

import logging
from typing import Callable, TypeVar, Any, Tuple, Type

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    retry_if_exception_type,
)

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

    def build_decorator(self) -> Callable:
        """
        Constrói um decorador Tenacity com base nas configurações.
        
        Retorna:
            Decorador @retry do Tenacity já configurado.
        """
        return retry(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(
                multiplier=self.initial_delay,
                min=self.initial_delay,
                max=self.max_delay,
                exp_base=self.backoff_multiplier,
            ),
            retry=retry_if_exception_type(self.exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )


def apply_retry(config: RetryConfig) -> Callable[[F], F]:
    """
    Decorador de resiliência com retry automático e backoff exponencial.
    
    Protege operações críticas de rede contra falhas temporárias, tentando
    novamente com delays exponenciais crescentes. Funciona com funções síncronas
    e assíncronas automaticamente via Tenacity.
    
    Args:
        config: Instância de RetryConfig com as configurações desejadas.
    
    Returns:
        Decorador que envolve a função com lógica de retry.
    
    Exemplo:
        # Retry com configuração padrão (síncono)
        @apply_retry(DATABASE_RETRY_CONFIG)
        def save_to_database(data):
            # Operação crítica
            pass
        
        # Retry com configuração customizada (assíncrono)
        @apply_retry(MESSAGING_RETRY_CONFIG)
        async def connect_to_rabbitmq():
            # Operação de conexão
            await some_async_operation()
    """
    return config.build_decorator()


# ====================================================================
# CONFIGURAÇÕES PRÉ-DEFINIDAS PARA CASOS DE USO COMUNS
# ====================================================================
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