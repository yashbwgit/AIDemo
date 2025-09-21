#!/usr/bin/env python3
"""
parse_cucumber_html.py

Usage:
  python parse_cucumber_html.py report.html output.csv

Parses a Cucumber HTML report and outputs a flat CSV containing
Feature, Scenario, Steps, Status, Duration, Error message and placeholders for AI Solution.
"""

import json
import re
import sys
from pathlib import Path
import pandas as pd

if len(sys.argv) < 3:
    print("Usage: python parse_cucumber_html.py input.html output.csv")
    sys.exit(1)

input_html = Path(sys.argv[1])
output_csv = Path(sys.argv[2])

html_text = input_html.read_text(encoding='utf-8')

# 1. Extract CUCUMBER_MESSAGES JSON array
pattern = re.compile(r'CUCUMBER_MESSAGES\s*=\s*(\[[\s\S]*?\]);', re.MULTILINE)
match = pattern.search(html_text)
if not match:
    raise RuntimeError("Could not find CUCUMBER_MESSAGES array in HTML")
messages = json.loads(match.group(1))

# 2. Build maps
features_map = {}        # feature_uri -> {feature_name, description, tags}
scenarios_map = {}       # testCaseId -> scenario info
steps_text_map = {}      # step_id -> text/keyword

scenario_runs = []       # testCaseStarted info
steps_rows = []          # final rows for CSV

# 3. First pass: get feature and scenario definitions
for msg in messages:
    if 'gherkinDocument' in msg:
        g = msg['gherkinDocument']
        if 'feature' in g:
            feat_name = g['feature'].get('name')
            feat_desc = g['feature'].get('description')
            feat_tags = [t['name'] for t in g['feature'].get('tags', [])]
            features_map[g.get('uri')] = {
                'feature_name': feat_name,
                'description': feat_desc,
                'tags': feat_tags,
                'scenarios': {}
            }
            # Steps text map for reference
            for child in g['feature'].get('children', []):
                if 'scenario' in child:
                    scen = child['scenario']
                    scenario_id = scen.get('id') or scen.get('name')
                    features_map[g.get('uri')]['scenarios'][scenario_id] = {
                        'scenario_name': scen.get('name'),
                        'tags': [t['name'] for t in scen.get('tags', [])],
                        'steps': scen.get('steps', [])
                    }
                    for st in scen.get('steps', []):
                        step_id = st.get('id') or (scenario_id + "_" + st.get('text'))
                        steps_text_map[step_id] = {
                            'text': st.get('text'),
                            'keyword': st.get('keyword')
                        }



# 4. Map testCaseId to scenario and feature using testCase and pickle
testCaseId_to_names = {}  # testCaseId -> (feature_name, scenario_name)
pickleId_to_pickle = {}   # pickleId -> pickle
for msg in messages:
    if 'pickle' in msg:
        pickle = msg['pickle']
        pickleId_to_pickle[pickle['id']] = pickle

for msg in messages:
    if 'testCase' in msg:
        testCase = msg['testCase']
        testCaseId = testCase['id']
        pickleId = testCase['pickleId']
        pickle = pickleId_to_pickle.get(pickleId)
        if pickle:
            scenario_name = pickle.get('name')
            uri = pickle.get('uri')
            feature = features_map.get(uri, {})
            feature_name = feature.get('feature_name')
            testCaseId_to_names[testCaseId] = (feature_name, scenario_name)

# 5. Capture testCaseStarted for scenario runs
testCaseStarted_by_id = {}
for msg in messages:
    if 'testCaseStarted' in msg:
        tcs = msg['testCaseStarted']
        testCaseStarted_by_id[tcs['id']] = tcs

# 6. Step events
step_started_times = {}
for msg in messages:
    if 'testStepStarted' in msg:
        tss = msg['testStepStarted']
        step_started_times[tss['testStepId']] = tss['timestamp']





# 7. Collect steps from scenario definition and errors from execution
scenario_steps = {}  # scenario_run_id -> {feature_name, scenario_name, steps: [], status, duration, error_message}
step_keywords = {'when', 'then', 'and', 'but'}
scenario_run_to_testCaseId = {}
for msg in messages:
    if 'testCaseStarted' in msg:
        tcs = msg['testCaseStarted']
        scenario_run_to_testCaseId[tcs['id']] = tcs.get('testCaseId')




# First, collect all scenario steps from the feature/scenario definition using testCase -> pickleId -> pickle
pickleId_to_steps = {}  # pickleId -> [step text]
for msg in messages:
    if 'pickle' in msg:
        pickle = msg['pickle']
        steps = []
        for step in pickle.get('steps', []):
            keyword = (step.get('keyword', '') or '').strip()
            text = (step.get('text', '') or '').strip()
            # Join keyword and text, even if no space
            if keyword and text:
                steps.append(f"{keyword}{text}")
            elif keyword:
                steps.append(keyword)
            elif text:
                steps.append(text)
        pickleId_to_steps[pickle['id']] = steps

testCaseId_to_pickleId = {}
for msg in messages:
    if 'testCase' in msg:
        testCase = msg['testCase']
        testCaseId = testCase['id']
        pickleId = testCase['pickleId']
        testCaseId_to_pickleId[testCaseId] = pickleId

# Now, collect execution results and errors
for msg in messages:
    if 'testStepFinished' in msg:
        tsf = msg['testStepFinished']
        result = tsf['testStepResult']
        scenario_run_id = tsf['testCaseStartedId']
        testCaseId = scenario_run_to_testCaseId.get(scenario_run_id)
        # Map to names
        scenario_name = None
        feature_name = None
        if testCaseId:
            names = testCaseId_to_names.get(testCaseId)
            if names:
                feature_name, scenario_name = names
        if scenario_run_id not in scenario_steps:
            steps = []
            if testCaseId:
                pickleId = testCaseId_to_pickleId.get(testCaseId)
                if pickleId:
                    steps = pickleId_to_steps.get(pickleId, [])
            scenario_steps[scenario_run_id] = {
                'feature_name': feature_name,
                'scenario_name': scenario_name,
                'scenario_run_id': scenario_run_id,
                'steps': steps,
                'step_status': 'PASSED',
                'step_duration_ms': 0.0,
                'error_message': '',
                'ai_solution': None
            }
        # Accumulate duration
        dur = result.get('duration', {})
        seconds = dur.get('seconds', 0)
        nanos = dur.get('nanos', 0)
        scenario_steps[scenario_run_id]['step_duration_ms'] += seconds * 1000 + nanos / 1e6
        # If any step failed, set error and status (append error if multiple)
        if result.get('status') != 'PASSED':
            scenario_steps[scenario_run_id]['step_status'] = result.get('status')
            err_msg = result.get('message')
            if err_msg:
                if scenario_steps[scenario_run_id]['error_message']:
                    scenario_steps[scenario_run_id]['error_message'] += '\n' + err_msg
                else:
                    scenario_steps[scenario_run_id]['error_message'] = err_msg


# AI Insights generator for failed scenarios
def generate_ai_insight(scenario, error_message, steps):
    if not error_message or not error_message.strip():
        return ""
    em = error_message.lower()
    step_text = '\n'.join(steps)
    if "element" in em and ("not found" in em or "unable to locate" in em or "no such element" in em):
        return (
            "Likely Cause:\n"
            "  - The test could not find a required UI element.\n"
            "  - This often happens when the application's UI has changed (element IDs, classes, or structure).\n"
            "Fix Steps:\n"
            "  1. Review recent UI changes.\n"
            "  2. Update the test's selectors/locators to match the new application structure.\n"
            "  3. Use more robust selectors (data-test-id, aria-label).\n"
            "  4. Add explicit waits for dynamic elements.\n"
            "Benefit:\n"
            "  - Ensures tests are resilient to UI changes.\n"
            "  - Reduces maintenance and boosts confidence in automation."
        )
    if "assert" in em or "expected" in em or "actual" in em:
        return (
            "Likely Cause:\n"
            "  - The application's behavior or data has changed, causing assertions to fail.\n"
            "Fix Steps:\n"
            "  1. Validate that the application's expected behavior matches the test.\n"
            "  2. Update test data or assertions as needed.\n"
            "  3. Collaborate with developers to confirm requirements.\n"
            "Benefit:\n"
            "  - Keeps tests aligned with business logic.\n"
            "  - Reduces false positives and improves trust in test results."
        )
    if "timeout" in em or "timed out" in em:
        return (
            "Likely Cause:\n"
            "  - The application or network is slower than expected.\n"
            "  - Asynchronous operations may not be handled.\n"
            "Fix Steps:\n"
            "  1. Add or increase waits/timeouts in the test.\n"
            "  2. Investigate application performance.\n"
            "  3. Use smart waits (wait for element visible/clickable).\n"
            "Benefit:\n"
            "  - Reduces flaky tests.\n"
            "  - Highlights real performance issues for a more robust CI pipeline."
        )
    if "stale element" in em:
        return (
            "Likely Cause:\n"
            "  - The DOM updated after the element was found, making the reference invalid.\n"
            "Fix Steps:\n"
            "  1. Refetch the element just before interacting.\n"
            "  2. Use waits to ensure the page is stable.\n"
            "Benefit:\n"
            "  - Prevents random failures.\n"
            "  - Improves test reliability on dynamic pages."
        )
    if "no such window" in em or "window closed" in em:
        return (
            "Likely Cause:\n"
            "  - The test tried to interact with a window or tab that was closed.\n"
            "Fix Steps:\n"
            "  1. Ensure the window/tab is open before interacting.\n"
            "  2. Add checks or error handling for window state.\n"
            "Benefit:\n"
            "  - Makes tests more robust in multi-window/tab scenarios."
        )
    # Generic fallback
    return (
        f"Likely Cause:\n  - Test failed with error: {error_message[:120]}...\n"
        "Fix Steps:\n  1. Review the failed step(s):\n     " + step_text.replace('\n', '\n     ') + "\n"
        "  2. Work with the dev team to identify root cause.\n  3. Update the test or application as needed.\n"
        "Benefit:\n  - Drives continuous improvement and transparency for all stakeholders."
    )

steps_rows = []
for run in scenario_steps.values():
    ai_solution = generate_ai_insight(run['scenario_name'], run['error_message'], run['steps'])
    steps_rows.append({
        'feature_name': run['feature_name'],
        'scenario_name': run['scenario_name'],
        'scenario_run_id': run['scenario_run_id'],
        'steps': '\n'.join(run['steps']),
        'step_status': run['step_status'],
        'step_duration_ms': run['step_duration_ms'],
        'error_message': run['error_message'],
        'ai_solution': ai_solution
    })

# Output columns: feature_name, scenario_name, scenario_run_id, steps, step_status, step_duration_ms, error_message, ai_solution
df = pd.DataFrame(steps_rows)
df.to_csv(output_csv, index=False)
print(f"Saved parsed data to {output_csv}")
