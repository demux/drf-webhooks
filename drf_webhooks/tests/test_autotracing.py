from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from .models import LevelOne, LevelOneSide, LevelThree, LevelTwo, Many


class AutoTracingTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create(username='testuser', password='12345')
        self.level_one = LevelOne.objects.create(name="LevelOne", owner=self.user)
        self.level_one_side = LevelOneSide.objects.create(name="LevelOneSide", one=self.level_one)
        self.many = Many.objects.create(name="Many")
        self.level_two = LevelTwo.objects.create(name="LevelTwo", parent=self.level_one)
        self.level_three = LevelThree.objects.create(name="LevelThree", parent=self.level_two)

    def test_many_to_many_field_defined_on_model_a(self):
        self.assertEqual(self.level_one.many.count(), 0)
        self.level_one.many.add(self.many)
        self.assertEqual(self.level_one.many.count(), 1)

    def test_many_to_many_field_defined_on_model_b(self):
        self.assertEqual(self.many.level_ones.count(), 0)
        self.many.level_ones.add(self.level_one)
        self.assertEqual(self.many.level_ones.count(), 1)

    def test_many_to_many_related_name_both_directions(self):
        self.assertEqual(self.level_one.many.count(), 0)
        self.level_one.many.add(self.many)
        self.assertEqual(self.level_one.many.count(), 1)
        self.assertEqual(self.many.level_ones.count(), 1)

    def test_many_to_many_related_query_name_both_directions(self):
        self.assertEqual(self.level_one.many.count(), 0)
        self.level_one.many.add(self.many)
        self.assertEqual(self.level_one.many.count(), 1)
        self.assertEqual(self.many.level_ones.filter(pk=self.level_one.pk).count(), 1)
        self.assertEqual(self.level_one.many.filter(pk=self.many.pk).count(), 1)

    def test_foreignkey_with_field_defined_on_model_A(self):
        self.assertEqual(self.level_one.owner, self.user)
        self.assertEqual(self.level_two.parent, self.level_one)
        self.assertEqual(self.level_three.parent, self.level_two)

    def test_foreignkey_with_field_defined_on_model_B(self):
        self.assertEqual(self.level_one.side, self.level_one_side)

    def test_foreignkey_with_related_name_both_directions(self):
        self.assertIn(self.level_two, self.level_one.leveltwo_set.all())
        self.assertEqual(self.level_two.parent, self.level_one)
        self.assertIn(self.level_three, self.level_two.levelthree_set.all())
        self.assertEqual(self.level_three.parent, self.level_two)

    def test_foreignkey_with_related_query_name_both_directions(self):
        self.assertIn(self.level_two, self.level_one.leveltwo_set.all())
        self.assertEqual(self.level_two.parent, self.level_one)


