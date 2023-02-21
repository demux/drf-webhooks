from rest_framework import serializers
from rest_framework.fields import flatten_choices_dict, to_choices_dict


class DynamicChoiceField(serializers.ChoiceField):
    @property
    def grouped_choices(self):
        return to_choices_dict(self.get_choices())

    @property
    def choice_strings_to_values(self):
        return {str(key): key for key in self.choices}

    @property
    def choices(self):
        return flatten_choices_dict(self.grouped_choices)

    @choices.setter
    def choices(self, callback):
        self.get_choices = callback
