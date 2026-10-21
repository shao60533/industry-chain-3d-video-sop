import sys,unittest
import subprocess
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from speech_plan import plan
class SpeechPlanTests(unittest.TestCase):
    def test_context_and_paragraph_not_single_sentence(self):
        p=plan('# 标题\n\nHBM属于DRAM。它负责高速供数。\n\n伙伴靠交付赚钱。')
        self.assertEqual(len(p['units']),2)
        self.assertEqual(p['units'][0]['text'],'HBM属于DRAM。它负责高速供数。')
        self.assertEqual(p['status'],'planned_pending_listening')
    def test_no_arbitrary_split_inside_product_or_number(self):
        text='一'*190+'百分之十一点六二。后一句。'
        p=plan(text)
        self.assertTrue(p['units'][0]['long_unit_warning'])
        self.assertIn('百分之十一点六二。',p['units'][0]['text'])
        self.assertEqual(''.join(x['text'] for x in p['units']),text)
    def test_sentence_group_context_and_no_auto_approval(self):
        p=plan('先看计算。再看互联。最后看软件。',maximum=8)
        self.assertEqual(len(p['units']),3)
        self.assertEqual(p['units'][1]['prior_context'],'先看计算。')
        self.assertTrue(all(x['boundary_review']=='pending' for x in p['units']))
    def test_repeated_sentence_keeps_its_actual_context(self):
        p=plan('先看计算。再看互联。先看计算。',maximum=6)
        self.assertEqual(p['units'][2]['prior_context'],'先看计算。再看互联。')
        self.assertEqual(p['units'][2]['next_context'],'')

    def test_repeated_punctuation_and_closing_quotes_are_preserved(self):
        for text in ('这是真的吗？！接着说明。', '他说：“先看计算。”再看互联。', '？！'):
            with self.subTest(text=text):
                value = plan(text, maximum=8)
                self.assertEqual(''.join(unit['text'] for unit in value['units']), text)

    def test_heading_without_blank_line_does_not_drop_narration(self):
        value = plan('# 标题\n正文先看计算。\n\n## 第二章\n正文再看互联。')
        self.assertEqual([unit['text'] for unit in value['units']], ['正文先看计算。', '正文再看互联。'])

    def test_cli_keeps_existing_outputs_and_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'script.md'
            output = Path(directory) / 'plan.json'
            source.write_text('中文原稿。', encoding='utf-8')
            output.write_text('existing plan', encoding='utf-8')
            script = Path(__file__).resolve().parents[1] / 'scripts/speech_plan.py'
            for destination in (output, source):
                result = subprocess.run([sys.executable, str(script), '--script', str(source), '--out', str(destination)], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(encoding='utf-8'), 'existing plan')
            self.assertEqual(source.read_text(encoding='utf-8'), '中文原稿。')
if __name__=='__main__':unittest.main()
