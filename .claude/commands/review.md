Run a full code review pipeline on the src/ directory:

1. Delegate to code-reviewer agent to review all Python files in src/ for 
   code quality, best practices and potential bugs
2. Delegate to python-reviewer agent to review for Python-specific issues, 
   type hints, and PEP8 compliance
3. Delegate to security-reviewer agent to check for security vulnerabilities, 
   exposed credentials, and API security issues
4. Collect all findings from the three reviews
5. If any issues were found, delegate to build-error-resolver to fix them
6. Report a final summary of what was reviewed, what was fixed, and 
   what still needs attention

Be systematic. Do not skip any agent. Report clearly after each step.