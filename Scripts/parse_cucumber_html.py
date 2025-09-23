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



# Senior QA AI insight generator for failed scenarios
def generate_ai_solution(scenario_name, error_message, steps):
    steps_preview = steps[:2] if isinstance(steps, list) else str(steps).split('\n')[:2]
    if not error_message or not str(error_message).strip():
        return ""
    scenario = scenario_name.lower() if scenario_name else ""
    em = error_message.lower() if error_message else ""


    # Expanded pattern list for robust QA coverage (now matches scenario name as well)
    patterns = [
        # Login and authentication
        (r'login with valid credentials containing special characters', "The application may not support special characters in credentials, causing login to fail.", ["Confirm requirements for allowed characters.", "Update backend validation and test data.", "Add user feedback for unsupported characters."], ["Ensures login works for all valid credential types.", "Improves user experience and reduces login issues."]),
        (r'login with valid long username and password', "The application may have length restrictions on username or password fields.", ["Check application and database field length limits.", "Update test data to match allowed lengths.", "Add validation and user feedback for excessive input."], ["Prevents user confusion and ensures only valid data is submitted.", "Reduces login failures due to input length."]),
        (r'login with empty username', "The application did not display the required error message for a missing username.", ["Ensure frontend validation is implemented for empty username fields.", "Add backend validation as a fallback.", "Update test to check for correct error message."], ["Improves user guidance and reduces login errors.", "Ensures compliance with UX standards."]),
        (r'login with valid username and empty password', "The application did not display the required error message for a missing password.", ["Ensure frontend validation is implemented for empty password fields.", "Add backend validation as a fallback.", "Update test to check for correct error message."], ["Improves user guidance and reduces login errors.", "Ensures compliance with UX standards."]),
        (r'login with both fields empty', "The application did not display the required error message for missing username and password.", ["Ensure frontend validation is implemented for both fields.", "Add backend validation as a fallback.", "Update test to check for correct error message."], ["Improves user guidance and reduces login errors.", "Ensures compliance with UX standards."]),
        (r'verify show password option', "The Show Password feature may not be implemented or is malfunctioning.", ["Verify the Show Password button triggers the correct UI event.", "Check for JavaScript errors or missing event handlers.", "Ensure password field type toggles between 'password' and 'text'."], ["Improves usability for users entering complex passwords.", "Reduces login errors due to mistyped passwords."]),
        (r'verify login button is disabled', "The Login button is not properly disabled when required fields are empty.", ["Add frontend validation to disable the button when fields are blank.", "Add backend validation to reject empty submissions.", "Update test to verify button state."], ["Prevents invalid login attempts.", "Improves user experience and reduces server load."]),
        (r'verify error message disappears', "The error message is not cleared after correcting credentials.", ["Ensure error messages are reset on input change or new login attempt.", "Update frontend logic to clear errors on valid input.", "Add test to verify error message disappears."], ["Improves user feedback and reduces confusion.", "Ensures error states do not persist incorrectly."]),
        (r'verify login form alignment', "The login form CSS or layout is incorrect, causing misalignment.", ["Review and update CSS for form alignment.", "Use layout tools (e.g., flexbox, grid) for consistent alignment.", "Add UI tests to catch alignment issues early."], ["Improves visual quality and user trust.", "Ensures accessibility and usability."]),
        # API, backend, and integration
        (r'api error|http 4\d\d|http 5\d\d|internal server error|service unavailable|bad gateway|502|503|504', "API/backend service returned an error.", ["Check backend service health and logs.", "Validate request payloads and endpoints.", "Add retry logic or fallback handling."], ["Improves system resilience.", "Reduces downtime impact."]),
        (r'invalid token|token expired|jwt expired|unauthorized|forbidden', "Authentication token is invalid or expired.", ["Check token generation and expiry policies.", "Ensure token is refreshed as needed.", "Update test to handle token renewal."], ["Prevents auth failures.", "Improves session management."]),
        (r'connection refused|connection reset|network error|timeout|timed out|dns error|host unreachable', "Network connectivity issue or service timeout.", ["Check network connection and endpoints.", "Increase timeout settings if appropriate.", "Retry operation or add error handling."], ["Improves reliability in unstable network conditions.", "Reduces test flakiness."]),
        (r'database error|sql error|db connection|constraint failed|deadlock|primary key|foreign key|unique constraint', "Database operation failed.", ["Check database connectivity and credentials.", "Review query logic and constraints.", "Resolve deadlocks or data conflicts."], ["Ensures data integrity.", "Reduces backend failures."]),
        (r'element not found|no such element|unable to locate|selector not found|stale element|element is not attached', "UI element was not found or became stale during test execution.", ["Check if the element selector is correct and stable.", "Ensure the UI has loaded before interacting.", "Update test to wait for element visibility or stability."], ["Reduces UI test flakiness.", "Improves test reliability."]),
        (r'assertion failed|expected .* but found|does not match|mismatch|assertEquals|assertTrue|assertFalse', "Test assertion did not match expected result.", ["Review test expectations and actual results.", "Update test or application logic as needed.", "Add clearer error messages for mismatches."], ["Improves test accuracy.", "Helps quickly identify root cause."]),
        (r'invalid input|validation failed|missing required|invalid format|data not found|required field|empty field|blank|input error', "Input data is missing or does not meet validation rules.", ["Review test data for required fields and formats.", "Update validation logic as needed.", "Add user feedback for invalid input."], ["Prevents data corruption.", "Improves user guidance and data quality."]),
        (r'file not found|cannot open file|resource missing|no such file|file missing|file not accessible', "File or resource required for the test is missing.", ["Check file paths and resource availability.", "Update test data setup.", "Add error handling for missing files."], ["Prevents test failures due to missing resources.", "Improves test setup robustness."]),
        (r'date mismatch|timezone error|invalid date|time drift|date format|date parse', "Date/time value is invalid or mismatched.", ["Check date/time formats and timezones.", "Synchronize clocks if needed.", "Update test data for valid date ranges."], ["Prevents time-based test failures.", "Improves data consistency."]),
        (r'session expired|state not saved|lost session|token expired|session timeout', "Session or state was lost or expired during test.", ["Increase session timeout if appropriate.", "Ensure state is saved between steps.", "Add re-authentication logic if needed."], ["Reduces session-related test failures.", "Improves user experience."]),
        (r'browser crashed|driver error|automation failed|webdriver|chrome not reachable|browser not reachable', "Browser or automation driver failed during test.", ["Update browser/driver versions.", "Check for compatibility issues.", "Add error handling for driver failures."], ["Improves automation stability.", "Reduces test interruptions."]),
        (r'permission denied|access denied|not authorized|forbidden|insufficient privileges', "User does not have the required permissions or role.", ["Check user roles and permissions.", "Update access control policies if needed.", "Add test coverage for permission boundaries."], ["Ensures only authorized users can access sensitive features.", "Reduces security risks."]),
        (r'intermittent|flaky|sometimes fails|race condition|sporadic|random failure', "Test is flaky or affected by timing/race conditions.", ["Add waits or synchronization in test.", "Stabilize environment and data setup.", "Log and monitor flaky test runs."], ["Improves test reliability.", "Reduces false negatives."]),
        (r'environment variable|config not set|missing configuration|env error|config missing|env not set', "Environment or configuration variable is missing or incorrect.", ["Check environment variable values.", "Update configuration files as needed.", "Add validation for required config at startup."], ["Prevents environment-specific failures.", "Improves deployment reliability."]),
        (r'out of memory|memory leak|heap space|stack overflow', "Application ran out of memory or has a memory leak.", ["Profile memory usage.", "Optimize memory-intensive operations.", "Increase memory allocation if needed."], ["Prevents crashes.", "Improves performance."]),
        (r'null pointer|type error|undefined is not a function|cannot read property', "Code error: null pointer or type error.", ["Check for null/undefined before accessing properties.", "Add error handling for missing objects.", "Update code to prevent type errors."], ["Prevents runtime errors.", "Improves code robustness."]),
        (r'build failed|compilation error|syntax error|parse error', "Build or compilation failed due to syntax or parse error.", ["Check code syntax.", "Fix parse errors.", "Update build scripts as needed."], ["Prevents build failures.", "Improves developer productivity."]),
        (r'not implemented|todo|pending implementation', "Feature or step is not yet implemented.", ["Implement the missing feature or step.", "Update test to reflect implemented functionality.", "Remove or skip test if not needed."], ["Ensures test coverage is accurate.", "Prevents false failures."]),
        (r'test data not found|missing test data|test data error', "Test data is missing or incorrect.", ["Check test data setup.", "Update test data files.", "Add validation for required test data."], ["Prevents test failures due to missing data.", "Improves test reliability."]),
        (r'email not received|email failed|smtp error|mailbox unavailable', "Email notification failed.", ["Check SMTP server configuration.", "Check spam/junk folder.", "Update email sending logic as needed."], ["Ensures notifications are delivered.", "Improves user communication."]),
        (r'payment failed|transaction declined|card error|insufficient funds', "Payment or transaction failed.", ["Check payment gateway logs.", "Validate card details and funds.", "Update error handling for payment failures."], ["Prevents revenue loss.", "Improves user experience."]),
        (r'access violation|segmentation fault|core dumped', "Critical runtime error: access violation or segmentation fault.", ["Check for invalid memory access.", "Update code to prevent out-of-bounds access.", "Add error handling for critical failures."], ["Prevents crashes.", "Improves application stability."]),
        (r'performance degraded|slow response|timeout|latency', "Performance issue: slow response or timeout.", ["Profile application performance.", "Optimize slow operations.", "Increase timeout thresholds if needed."], ["Improves user experience.", "Reduces timeouts."]),
        (r'circular dependency|dependency error|module not found', "Dependency or module error.", ["Check dependency installation.", "Update module paths.", "Fix circular dependencies."], ["Prevents runtime errors.", "Improves build reliability."]),
        (r'permission error|file permission|access is denied', "File or resource permission error.", ["Check file and directory permissions.", "Update access rights as needed.", "Add error handling for permission issues."], ["Prevents access errors.", "Improves security."]),
        (r'api limit|rate limit|too many requests|quota exceeded', "API rate limit or quota exceeded.", ["Reduce request frequency.", "Implement exponential backoff.", "Monitor API usage and quotas."], ["Prevents service disruption.", "Improves reliability."]),
        (r'captcha required|captcha failed|robot check', "CAPTCHA or bot check failed.", ["Update test to handle CAPTCHA.", "Request manual intervention if needed.", "Contact support for test bypass."], ["Prevents automation blockages.", "Improves test automation coverage."]),
        (r'license expired|license not found|activation failed', "License or activation error.", ["Check license validity.", "Update license files.", "Contact vendor for support."], ["Prevents service disruption.", "Ensures compliance."]),
        (r'feature flag|flag not enabled|feature not available', "Feature flag or toggle is not enabled.", ["Enable the required feature flag.", "Update test to check flag status.", "Coordinate with product team for rollout."], ["Ensures correct feature availability.", "Prevents false failures."]),
        (r'api deprecated|deprecated endpoint|obsolete api', "API endpoint is deprecated or obsolete.", ["Update to use supported API endpoints.", "Coordinate with API provider for migration.", "Update documentation and tests."], ["Prevents future failures.", "Ensures compatibility."]),
        (r'overflow|underflow|divide by zero', "Mathematical error: overflow, underflow, or divide by zero.", ["Check calculations for edge cases.", "Add error handling for math errors.", "Update test data to avoid invalid operations."], ["Prevents runtime errors.", "Improves calculation reliability."]),
        (r'ui not responsive|unresponsive|ui freeze|ui hang', "UI became unresponsive or froze during test.", ["Profile UI performance.", "Optimize rendering logic.", "Add monitoring for UI hangs."], ["Improves user experience.", "Prevents UI freezes."]),
        (r'api schema mismatch|contract violation|unexpected response', "API response schema mismatch or contract violation.", ["Update API contract tests.", "Coordinate with backend team for schema changes.", "Update client code for new schema."], ["Prevents integration failures.", "Ensures contract compliance."]),
        (r'csrf token|cross-site request forgery|csrf error', "CSRF token or security error.", ["Check CSRF token handling.", "Update security configuration.", "Add test for CSRF protection."], ["Prevents security vulnerabilities.", "Improves application safety."]),
        (r'xpath error|invalid xpath|xpath not found', "XPath selector error.", ["Check XPath expressions.", "Update selectors for UI changes.", "Add error handling for invalid XPath."], ["Prevents selector failures.", "Improves UI test reliability."]),
        (r'api timeout|gateway timeout|upstream timeout', "API or gateway timeout.", ["Check upstream service health.", "Increase timeout thresholds.", "Add retry logic for timeouts."], ["Prevents service disruption.", "Improves reliability."]),
    ]

    # Try to match scenario name, error message, and steps for patterns
    context_blob = f"{scenario}\n{em}\n" + '\n'.join(steps_preview)
    for pat, cause, fix_steps, benefits in patterns:
        if re.search(pat, context_blob):
            return (
                f"Likely Cause:\n  - {cause}\n"
                f"Fix Steps:\n  " + '\n  '.join(f"{i+1}. {step}" for i, step in enumerate(fix_steps)) + "\n"
                f"Benefits:\n  - " + '\n  - '.join(benefits)
            )

    # Generic fallback: context-aware expert QA insight
    return (
        f"Likely Cause:\n  - Test failed for scenario: '{scenario_name}'. Error: {error_message[:120]}...\n"
        "Fix Steps:\n  1. Review the failed step(s):\n     " + '\n     '.join(steps_preview) + "\n  2. Analyze the error message and logs for root cause.\n  3. Collaborate with developers to resolve the defect.\n  4. Update the test or application as needed.\n"
        "Benefits:\n  - Drives continuous improvement and transparency for all stakeholders.\n  - Reduces recurrence of similar issues in the future."
    )

steps_rows = []
for run in scenario_steps.values():
    ai_solution = ''
    if run['step_status'] == 'FAILED':
        ai_solution = generate_ai_solution(run['scenario_name'], run['error_message'], run['steps'])
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
