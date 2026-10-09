import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('precheck', Path(__file__).resolve().parents[1]/'scripts/iam-grant-precheck.py')
precheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(precheck)

class Boundaries(unittest.TestCase):
    def test_write_cannot_reach_process(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(precheck.capture.subprocess,'run') as proc:
            for operation in ['create-role','attach-role-policy','put-user-policy','delete-policy']:
                with self.assertRaisesRegex(RuntimeError,'blocked'):
                    precheck.capture.Capture(Path(tmp)).call('bad','iam',operation)
            proc.assert_not_called()

    def test_wrong_caller_stops_and_preserves_receipt(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(precheck.os.environ,{},clear=True), patch.object(precheck.platform,'node',return_value='fixture'), patch.object(precheck.platform,'platform',return_value='fixture'):
            with patch.object(precheck.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'aws-cli/test',b'')):
                with patch.object(precheck.capture.Capture,'call',return_value={'Account':'other','Arn':'wrong'}) as call:
                    with self.assertRaisesRegex(RuntimeError,'Caller mismatch'):
                        precheck.run(Path(tmp),'arn:aws:iam::774055931866:root')
                    self.assertEqual(call.call_count,1)
                    summary=json.loads(next(Path(tmp).glob('*/summary.json')).read_text())
                    self.assertEqual(summary['status'],'INCOMPLETE')
                    self.assertEqual(summary['aws_mutation'],'NOT_RUN')
                    self.assertIn('Caller mismatch',summary['error'])

if __name__ == '__main__':
    unittest.main()
