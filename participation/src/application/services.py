"""
Módulo: services.py
Descrição: Orquestra os Casos de Uso (Use Cases) e centraliza as regras de negócio 
do subdomínio Participation. Atua como o "motor lógico" da aplicação: recebe os 
comandos da camada HTTP (routers), aplica as validações de elegibilidade exigidas 
(como bloqueio de adesão duplicada ou valor negativo) e interage com a camada de 
infraestrutura (banco de dados/repositórios) para salvar ou consultar as informações. 
É estritamente nesta camada que as Regras de Negócio (RN01 a RN04) são executadas.
"""
