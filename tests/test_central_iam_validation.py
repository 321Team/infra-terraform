"""Failure-boundary tests only. No AWS calls or permission simulation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('central',Path(__file__).resolve().parents[1]/'scripts/central-iam-validation.py')
central = importlib.util.module_from_spec(spec)
spec.loader.exec_module(central)

class SafetyTests(unittest.TestCase):
    def test_missing_context_never_passes_denial(self):
        row={'EvaluationResults':[{'EvalDecision':'implicitDeny','MissingContextValues':['aws:ResourceTag/Project']}]}
        self.assertEqual(central.verdict({'expected':'implicitDeny','diagnostic_only':False},row),'MISSING_CONTEXT_REVIEW')

    def test_resource_denial_overrides_overall_allow(self):
        row={'EvaluationResults':[{'EvalDecision':'allowed','ResourceSpecificResults':[{'EvalResourceDecision':'implicitDeny'}]}]}
        self.assertEqual(central.verdict({'expected':'allowed','diagnostic_only':False},row),'MISMATCH')

    def test_diagnostic_is_not_a_pass(self):
        row={'EvaluationResults':[{'EvalDecision':'implicitDeny'}]}
        self.assertEqual(central.verdict({'expected':'implicitDeny','diagnostic_only':True},row),'DIAGNOSTIC_EXPECTED')

    def test_mutation_is_rejected_before_process(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(central.subprocess,'run') as proc:
            with self.assertRaisesRegex(RuntimeError,'blocked'):
                central.Capture(Path(tmp)).call('bad','iam','create-role')
            proc.assert_not_called()

    def test_access_denied_is_not_absence(self):
        with tempfile.TemporaryDirectory() as tmp:
            response=subprocess.CompletedProcess([],254,b'',b'An error occurred (AccessDenied)')
            with patch.object(central.subprocess,'run',return_value=response):
                cap=central.Capture(Path(tmp))
                with self.assertRaisesRegex(RuntimeError,'API failed'):
                    cap.call('role','iam','get-role',absent=True)
                self.assertEqual(cap.records[0]['exit_code'],254)

    def test_tampered_request_stops_before_aws(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/'bundle'; bundle.mkdir()
            (bundle/'request.json').write_text('{}')
            central.write(bundle/'manifest.json',{'request.json':'0'*64})
            with patch.dict(central.os.environ, {}, clear=True), patch.object(central.subprocess,'run') as proc:
                with self.assertRaisesRegex(RuntimeError,'hash mismatch'):
                    central.run(bundle,Path(tmp),f'arn:aws:iam::{central.ACCOUNT}:root')
                proc.assert_not_called()

    def test_endpoint_and_ca_overrides_stop_before_aws(self):
        for key in ['AWS_CA_BUNDLE','AWS_DATA_PATH','AWS_ENDPOINT_URL','AWS_ENDPOINT_URL_IAM']:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                with patch.dict(central.os.environ, {key:'review-required'}, clear=True), patch.object(central.subprocess,'run') as proc:
                    with self.assertRaisesRegex(RuntimeError,'Review environment overrides'):
                        central.run(Path(tmp)/'absent-bundle',Path(tmp),f'arn:aws:iam::{central.ACCOUNT}:root')
                    proc.assert_not_called()

    def test_timeout_preserves_failure_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(central.subprocess,'run',side_effect=subprocess.TimeoutExpired(['aws'],60,output=b'partial')):
                cap=central.Capture(Path(tmp))
                with self.assertRaisesRegex(RuntimeError,'API failed'):
                    cap.call('identity','sts','get-caller-identity')
                self.assertTrue(cap.records[0]['timeout'])
                self.assertIsNone(cap.records[0]['exit_code'])
                self.assertEqual((Path(tmp)/'identity.stdout').read_bytes(),b'partial')

if __name__=='__main__':
    unittest.main()
