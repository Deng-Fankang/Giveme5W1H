import logging

#
# Random metric, it will always return a distance between 0 and 1
class Enhancement():

    def __init__(self, config):
        self.log = logging.getLogger('GiveMe5W')
        self.log.info('Enhancer initialised')

    def process(self, documents):
        self.log.info('            ')
        self.log.info('      Enhancer process:')

        self.log.info('            AIDA')
        self.log.info('            ')