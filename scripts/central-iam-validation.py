"""Read-only AWS policy validation. No grant, resource mutation, or Terraform calls.

prepare builds reviewable requests offline. run requires an exact expected STS ARN.
Simulation IDs are fictitious; these are policy tests, never resource inventory.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

SOURCE = 'd857c63c6e5b3800b746511ffa8b913e350d27ce'
ACCOUNT = '774055931866'
REGION = 'ap-northeast-2'
ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / 'iam/full-policy-draft-20261009'
IAC = ['FDS-IaC-State-PassRole', 'FDS-IaC-Network', 'FDS-IaC-Vpn', 'FDS-IaC-Guardrails']
ALLOWED = {('sts', 'get-caller-identity'), ('iam', 'get-role'),
           ('iam', 'list-attached-role-policies'), ('iam', 'list-role-policies'),
           ('iam', 'get-role-policy'), ('iam', 'get-policy'), ('iam', 'get-policy-version'),
           ('accessanalyzer', 'validate-policy'), ('iam', 'simulate-custom-policy')}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def policies(names):
    return [(DRAFT / 'policies' / (name + '.json')).read_text(encoding='utf-8') for name in names]

def cases():
    ec2 = f'arn:aws:ec2:{REGION}:{ACCOUNT}:'
    arn = {k: ec2 + k + '/' + v for k, v in {
        'vpc':'vpc-00000000000000001', 'subnet':'subnet-00000000000000001',
        'route-table':'rtb-00000000000000001', 'instance':'i-00000000000000001',
        'volume':'vol-00000000000000001', 'security-group':'sg-00000000000000001',
        'security-group-rule':'sgr-00000000000000001', 'network-interface':'eni-00000000000000001',
        'natgateway':'nat-00000000000000001', 'elastic-ip':'eipalloc-00000000000000001'}.items()}
    role = f'arn:aws:iam::{ACCOUNT}:role/FDS-Relay-SSM'
    state = f'arn:aws:s3:::fds-tfstate-{ACCOUNT}-{REGION}/phase2/network/terraform.tfstate'
    document = f'arn:aws:ssm:{REGION}:{ACCOUNT}:document/SSM-SessionManagerRunShell'
    image = f'arn:aws:ec2:{REGION}::image/ami-08d855918a18d0cf9'
    base = {'aws:RequestedRegion': REGION, 'aws:PrincipalArn': f'arn:aws:iam::{ACCOUNT}:role/FDS-IaC-Operator', 'aws:SecureTransport': True}
    req = {'aws:RequestTag/Project':'fds-hybrid', 'aws:RequestTag/ManagedBy':'terraform'}
    own = {'aws:ResourceTag/Project':'fds-hybrid', 'aws:ResourceTag/ManagedBy':'terraform'}
    foreign = {'aws:ResourceTag/Project':'other-project', 'aws:ResourceTag/ManagedBy':'other-owner'}
    run = {**req, 'ec2:InstanceType':'t3.medium', 'ec2:MetadataHttpTokens':'required'}
    vol = {'ec2:VolumeType':'gp3', 'ec2:Encrypted':True, 'ec2:VolumeSize':40}
    result = []
    def add(cid, action, resource, context, expected, names=IAC, diagnostic=False):
        context = {**base, **context}
        entries = []
        for key, val in context.items():
            typ = 'boolean' if isinstance(val, bool) else 'numeric' if isinstance(val, int) else 'stringList' if isinstance(val, list) else 'string'
            vals = val if isinstance(val, list) else [str(val).lower() if isinstance(val, bool) else str(val)]
            entries.append({'ContextKeyName':key, 'ContextKeyValues':vals, 'ContextKeyType':typ})
        result.append({'id':cid, 'expected':expected, 'diagnostic_only':diagnostic,
                       'request': {'PolicyInputList': policies(names), 'ActionNames':[action],
                                   'ResourceArns':[resource], 'ContextEntries':entries}})
    add('P1','ec2:CreateVpc',arn['vpc'],req,'allowed')
    add('P2-subnet','ec2:CreateSubnet',arn['subnet'],req,'allowed')
    add('P2-parent','ec2:CreateSubnet',arn['vpc'],own,'allowed',diagnostic=True)
    add('P3','ec2:CreateTags',arn['vpc'],{**req,'ec2:CreateAction':'CreateVpc'},'allowed')
    add('P4','ec2:CreateRoute',arn['route-table'],own,'allowed')
    for key, ctx in [('instance',run),('volume',vol),('subnet',own),('security-group',own),('network-interface',{})]:
        add('P5-'+key,'ec2:RunInstances',arn[key],ctx,'allowed',diagnostic=True)
    add('P5-image','ec2:RunInstances',image,{},'allowed',diagnostic=True)
    add('P6','iam:PassRole',role,{'iam:PassedToService':'ec2.amazonaws.com'},'allowed')
    add('P7','s3:PutObject',state,{},'allowed')
    add('P8','s3:DeleteObject',state+'.tflock',{},'allowed')
    add('P9','kms:DescribeKey',f'arn:aws:kms:{REGION}:{ACCOUNT}:key/00000000-0000-0000-0000-000000000001',{'kms:RequestAlias':'alias/aws/ebs'},'allowed')
    add('P10','ec2:ModifyInstanceMetadataOptions',arn['instance'],{**own,'ec2:MetadataHttpTokens':'required'},'allowed')
    add('P11','ec2:CreateTags',arn['security-group-rule'],{**own,**req},'allowed')
    add('P12','ec2:DescribeAddressesAttribute','*',{},'allowed')
    for key, ctx in [('natgateway',req),('subnet',own),('elastic-ip',own)]:
        add('P13-'+key,'ec2:CreateNatGateway',arn[key],ctx,'allowed',diagnostic=True)
    add('P14','ec2:AllocateAddress',arn['elastic-ip'],req,'allowed')
    for key, action in [('natgateway','ec2:DeleteNatGateway'),('elastic-ip','ec2:ReleaseAddress')]:
        add('P15-'+key,action,arn[key],own,'allowed')
        add('N26-'+key,action,arn[key],foreign,'implicitDeny')
    # Wrong values isolate scope denials without treating missing context as a pass.
    add('N1-wrong-project','ec2:CreateVpc',arn['vpc'],{**req,'aws:RequestTag/Project':'other-project'},'implicitDeny')
    add('N1-omitted-project','ec2:CreateVpc',arn['vpc'],{'aws:RequestTag/ManagedBy':'terraform'},'implicitDeny',diagnostic=True)
    add('N2','ec2:CreateVpc',arn['vpc'],{**req,'aws:RequestedRegion':'us-east-1'},'explicitDeny')
    add('N3','ec2:DeleteVpc',arn['vpc'],foreign,'implicitDeny')
    add('N4','ec2:DeleteTags',arn['vpc'],{**own,'aws:TagKeys':['Project']},'explicitDeny')
    add('N5','ec2:CreateTags',arn['vpc'],{**foreign,**req,'ec2:CreateAction':'not-a-create-call'},'implicitDeny')
    add('N6','ec2:CreateTags',arn['vpc'],{**own,**req,'aws:RequestTag/Project':'other-project'},'explicitDeny')
    add('N7','ec2:AssociateAddress',arn['elastic-ip'],foreign,'implicitDeny')
    add('N8','ec2:RunInstances',arn['instance'],{**run,'ec2:InstanceType':'t3.large'},'explicitDeny')
    add('N9','ec2:RunInstances',arn['instance'],{**run,'ec2:MetadataHttpTokens':'optional'},'explicitDeny')
    add('N10','ec2:RunInstances',image.replace('ami-08d855918a18d0cf9','ami-00000000000000002'),{},'implicitDeny')
    add('N11-unencrypted','ec2:RunInstances',arn['volume'],{**vol,'ec2:Encrypted':False},'implicitDeny')
    add('N11-oversized','ec2:RunInstances',arn['volume'],{**vol,'ec2:VolumeSize':100},'implicitDeny')
    add('N12-role','iam:PassRole',role+'-other',{'iam:PassedToService':'ec2.amazonaws.com'},'implicitDeny')
    add('N12-service','iam:PassRole',role,{'iam:PassedToService':'lambda.amazonaws.com'},'implicitDeny')
    add('N13','s3:DeleteObject',state,{},'explicitDeny')
    add('N13-version','s3:DeleteObjectVersion',state,{},'explicitDeny')
    add('N14','s3:PutObject',state.replace('/network/','/other/'),{},'implicitDeny')
    for action in ['ssm:UpdateDocument','ssm:SendCommand']:
        add('N15-'+action.split(':')[1],action,document,{},'explicitDeny')
    add('N16','cloudformation:UpdateStack',f'arn:aws:cloudformation:{REGION}:{ACCOUNT}:stack/fds-review-fixture/00000000-0000-0000-0000-000000000001',{},'explicitDeny')
    add('N17','ec2:DeleteNetworkInterface',arn['network-interface'],own,'implicitDeny')
    add('N18','s3:GetObject',state,{},'explicitDeny',['FDS-Network-Operator-StateDeny'])
    add('N19','s3:GetObject',state,{},'explicitDeny',['FDS-ReadOnly-Audit-StateDeny'])
    add('N24','ec2:ModifyInstanceMetadataOptions',arn['instance'],{**own,'ec2:MetadataHttpTokens':'optional'},'explicitDeny')
    add('N25','ec2:CreateTags',arn['security-group-rule'],{**foreign,**req,'ec2:CreateAction':'not-a-create-call'},'implicitDeny')
    # Simulator contexts are request-wide, not per-resource service context.
    # Paired probes expose overlaps, but NEVER establish multi-resource safety.
    for cid, action, key in [('N20','ec2:CreateSubnet','vpc'),('N21','ec2:CreateRouteTable','vpc'),
                             ('N22-subnet','ec2:CreateNatGateway','subnet'),('N22-eip','ec2:CreateNatGateway','elastic-ip'),
                             ('N23-subnet','ec2:RunInstances','subnet'),('N23-sg','ec2:RunInstances','security-group')]:
        add('P-split-'+cid,action,arn[key],{**own,**run},'allowed',diagnostic=True)
        add(cid+'-parent-scope',action,arn[key],foreign,'implicitDeny',diagnostic=True)
        add(cid+'-request-context',action,arn[key],{**foreign,**run},'implicitDeny',diagnostic=True)
    return result

def prepare(out):
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    checks = {}
    for line in (DRAFT / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split(' *', 1)
        actual = digest(DRAFT / name)
        if actual != expected:
            raise RuntimeError('Source hash mismatch: ' + name)
        checks[name] = actual
    work = out / 'requests'
    work.mkdir(mode=0o700)
    all_cases = cases()
    for case in all_cases:
        write(work / (case['id'] + '.json'), case['request'])
    write(out / 'cases.json', [{k:v for k,v in case.items() if k != 'request'} for case in all_cases])
    # Copy source policy bytes, never rewrite reviewed JSON.
    shutil.copytree(DRAFT / 'policies', out / 'policies')
    shutil.copytree(DRAFT / 'trust', out / 'trust')
    write(out / 'source.json', {'source_sha':SOURCE,'policy_hashes':checks,'collector_sha256':digest(__file__),
                              'scope':'SYNTHETIC_POLICY_SIMULATION_NOT_LIVE_RESOURCES',
                              'multiresource':'REQUIRES_SERVICE_SEMANTICS_REVIEW; paired probes are diagnostics only'})
    manifest = {p.relative_to(out).as_posix():digest(p) for p in out.rglob('*') if p.is_file()}
    write(out / 'manifest.json', manifest)
    print(json.dumps({'prepared':str(out), 'cases':len(all_cases), 'aws_calls':0}))

class Capture:
    def __init__(self, out):
        self.out = out
        self.records = []
        # Force official AWS endpoints; no inherited profile/service endpoint redirect.
        self.env = dict(os.environ, AWS_PAGER='', AWS_CLI_AUTO_PROMPT='off', AWS_IGNORE_CONFIGURED_ENDPOINT_URLS='true')
    def call(self, name, service, operation, args=(), absent=False):
        if (service, operation) not in ALLOWED:
            raise RuntimeError('Mutation or unreviewed operation blocked')
        argv = ['aws',service,operation,*args,'--region',REGION,'--output','json','--no-cli-pager',
                '--cli-connect-timeout','10','--cli-read-timeout','30']
        rec = {'name':name,'argv':argv,'started_utc':now()}
        try:
            p = subprocess.run(argv, capture_output=True, timeout=60, env=self.env)
            stdout, stderr, rc = p.stdout, p.stderr, p.returncode
            rec['timeout'] = False
        except subprocess.TimeoutExpired as e:
            stdout, stderr, rc = e.stdout or b'', e.stderr or b'', None
            rec['timeout'] = True
        (self.out/(name+'.stdout')).write_bytes(stdout)
        (self.out/(name+'.stderr')).write_bytes(stderr)
        rec.update(finished_utc=now(), exit_code=rc, stdout_sha256=hashlib.sha256(stdout).hexdigest(), stderr_sha256=hashlib.sha256(stderr).hexdigest())
        self.records.append(rec)
        if rc != 0:
            if absent and rc is not None and b'(NoSuchEntity)' in stderr:
                return {'observed':'ABSENT'}
            raise RuntimeError('API failed; see private evidence: ' + name)
        return json.loads(stdout)

def verdict(case, response):
    results = response.get('EvaluationResults', [])
    if len(results) != 1:
        return 'INCOMPLETE'
    row = results[0]
    missing = set(row.get('MissingContextValues', []))
    specific = row.get('ResourceSpecificResults', [])
    for item in specific:
        missing.update(item.get('MissingContextValues', []))
    if missing:
        return 'MISSING_CONTEXT_REVIEW'
    match = row.get('EvalDecision') == case['expected'] and all(x.get('EvalResourceDecision') == case['expected'] for x in specific)
    if case['diagnostic_only']:
        return 'DIAGNOSTIC_EXPECTED' if match else 'DIAGNOSTIC_MISMATCH_REVIEW'
    return 'SIMULATION_MATCH' if match else 'MISMATCH'

def run(bundle, parent, expected_arn):
    if not expected_arn.startswith(f'arn:aws:') or f':{ACCOUNT}:' not in expected_arn or '*' in expected_arn:
        raise RuntimeError('Exact expected central caller ARN required')
    unsafe = [k for k in os.environ if k.startswith('AWS_ENDPOINT_URL') or k in ('AWS_CA_BUNDLE','AWS_DATA_PATH')]
    if unsafe:
        raise RuntimeError('Review environment overrides first: ' + ','.join(unsafe))
    manifest = load(bundle/'manifest.json')
    actual_files = {p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file()} - {'manifest.json'}
    if actual_files != set(manifest) or any(digest(bundle/p) != h for p,h in manifest.items()):
        raise RuntimeError('Bundle file set/hash mismatch')
    if load(bundle/'source.json')['collector_sha256'] != digest(__file__):
        raise RuntimeError('Collector changed after prepare')
    out = Path(tempfile.mkdtemp(prefix='fds-central-iam-',dir=parent))
    out.chmod(0o700)
    cap = Capture(out)
    summary = {'started_utc':now(),'host':platform.node(),'platform':platform.platform(),'source':load(bundle/'source.json'),
               'input_manifest_sha256':digest(bundle/'manifest.json'),'expected_caller_arn':expected_arn,
               'aws_mutation':'NOT_RUN','grant':'NOT_RUN','cloud_plan':'NOT_RUN','status':'INCOMPLETE'}
    try:
        cli = subprocess.run(['aws','--version'],capture_output=True,timeout=10)
        (out/'aws-version.stdout').write_bytes(cli.stdout)
        (out/'aws-version.stderr').write_bytes(cli.stderr)
        summary['aws_cli_version_rc'] = cli.returncode
        if cli.returncode != 0:
            raise RuntimeError('AWS CLI version capture failed')
        identity = cap.call('identity','sts','get-caller-identity')
        if identity.get('Account') != ACCOUNT or identity.get('Arn') != expected_arn:
            raise RuntimeError('Caller/account mismatch: STOP')
        # Fresh role inventory; original policy contents remain private.
        for role in ['FDS-IaC-Operator','FDS-Network-Operator','FDS-ReadOnly-Audit']:
            before = cap.call('before-'+role,'iam','get-role',['--role-name',role],absent=True)
            if before.get('observed') == 'ABSENT':
                continue
            attached = cap.call('attached-'+role,'iam','list-attached-role-policies',['--role-name',role])
            inline = cap.call('inline-'+role,'iam','list-role-policies',['--role-name',role])
            for i, name in enumerate(inline.get('PolicyNames', [])):
                cap.call(f'inline-{role}-{i}','iam','get-role-policy',['--role-name',role,'--policy-name',name])
            for i, item in enumerate(attached.get('AttachedPolicies', [])):
                p = cap.call(f'attached-{role}-{i}','iam','get-policy',['--policy-arn',item['PolicyArn']])
                cap.call(f'attached-{role}-{i}-version','iam','get-policy-version',['--policy-arn',item['PolicyArn'],'--version-id',p['Policy']['DefaultVersionId']])
        audit = 'arn:aws:iam::aws:policy/job-function/ViewOnlyAccess'
        p = cap.call('audit-managed-policy','iam','get-policy',['--policy-arn',audit])
        cap.call('audit-managed-version','iam','get-policy-version',['--policy-arn',audit,'--version-id',p['Policy']['DefaultVersionId']])
        findings = []
        for directory in ['policies','trust']:
            for path in sorted((bundle/directory).glob('*.json')):
                if '.template.' in path.name:
                    continue  # Exact Relay instance binding is unavailable; no invented live ARN.
                trust = path.name.startswith('trust-')
                args = ['--policy-document',path.resolve().as_uri(),'--policy-type','RESOURCE_POLICY' if trust else 'IDENTITY_POLICY']
                if trust:
                    args += ['--validate-policy-resource-type','AWS::IAM::AssumeRolePolicyDocument']
                res = cap.call('validate-'+path.stem,'accessanalyzer','validate-policy',args)
                findings += [{'file':directory+'/'+path.name,**f} for f in res.get('findings',[])]
        summary['findings'] = findings
        if any(f.get('findingType') in ['ERROR','SECURITY_WARNING'] for f in findings):
            summary['status'] = 'VALIDATION_REVIEW_REQUIRED'
            return out
        outcomes = []
        for case in load(bundle/'cases.json'):
            res = cap.call('sim-'+case['id'],'iam','simulate-custom-policy',
                           ['--cli-input-json',(bundle/'requests'/(case['id']+'.json')).resolve().as_uri()])
            outcomes.append({'id':case['id'],'verdict':verdict(case,res),'expected':case['expected']})
        summary['cases'] = outcomes
        summary['status'] = 'CAPTURE_COMPLETE_REVIEW_REQUIRED'
        summary['multi_resource_gate'] = 'NOT_PROVEN_BY_SIMULATOR'
        return out
    except Exception as exc:
        summary['error'] = str(exc)
        raise
    finally:
        summary.update(finished_utc=now(),records=cap.records)
        write(out/'summary.json',summary)
        write(out/'capture-manifest.json',{p.name:digest(p) for p in out.iterdir() if p.is_file()})
        print(json.dumps({'capture':str(out),'status':summary['status'],'aws_mutation':'NOT_RUN'}))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode',required=True)
    prep = sub.add_parser('prepare'); prep.add_argument('--output',type=Path,required=True)
    live = sub.add_parser('run'); live.add_argument('--bundle',type=Path,required=True)
    live.add_argument('--output-parent',type=Path,required=True)
    live.add_argument('--expected-caller-arn',required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if args.mode == 'prepare':
        prepare(args.output)
    else:
        run(args.bundle,args.output_parent,args.expected_caller_arn)

if __name__ == '__main__':
    main()
