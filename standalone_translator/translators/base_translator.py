from abc import ABC, abstractmethod

class BaseTranslator(ABC):
    """
    Abstract base class for all translator providers.
    Each provider must implement the 'translate' method.
    """

    @abstractmethod
    def translate(self, batch_data, model_name, history, character_config):
        """
        Translates a batch of data.

        :param batch_data: A list of dicts, where each dict contains speaker and dialogue.
        :param model_name: The name of the AI model to use.
        :param history: The conversational history from previous batches.
        :param character_config: A dict containing character definitions.
        :return: A tuple containing (list_of_translated_strings, updated_history).
        """
        pass
