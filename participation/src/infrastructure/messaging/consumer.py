"""
Módulo: consumer.py
Descrição: Worker de Mensageria Assíncrona (Asynchronous Messaging).
Roda em uma thread/processo de segundo plano para escutar o RabbitMQ.
Seu objetivo principal é reagir a eventos (como 'UserDeactivated') disparados 
por outros domínios, garantindo que as participações sejam canceladas 
automaticamente sem depender de chamadas síncronas.
"""