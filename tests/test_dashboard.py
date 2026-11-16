import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
class DashboardTests(unittest.TestCase):
 def test_filters_search_and_empty_selection(self):
  at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90).run()
  self.assertFalse(at.exception)
  at.multiselect[0].set_value(['kk']).run();self.assertFalse(at.exception)
  next(x for x in at.selectbox if x.label=='Категория').set_value('Technology').run();self.assertFalse(at.exception)
  next(x for x in at.selectbox if x.label=='Тема').set_value('Artificial intelligence').run();self.assertFalse(at.exception)
  at.text_input[0].set_value("' OR 1=1 --").run();self.assertFalse(at.exception)
  at.multiselect[0].set_value([]).run();self.assertFalse(at.exception)
