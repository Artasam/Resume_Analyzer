import re

_SKILLS_DATABASE = {
    'Python', 'Java', 'JavaScript', 'C++', 'C#', 'PHP', 'Ruby', 'Swift', 'Kotlin', 'Go', 'Rust',
    'TypeScript', 'Scala', 'Perl', 'R', 'MATLAB', 'SQL', 'HTML', 'CSS', 'Bash', 'PowerShell',
    'React', 'Angular', 'Vue.js', 'Node.js', 'Express.js', 'Django', 'Flask', 'Spring', 'Laravel',
    'WordPress', 'Drupal', 'Joomla', 'Bootstrap', 'jQuery', 'AJAX', 'REST API', 'GraphQL',
    'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Oracle', 'SQLite', 'Cassandra',
    'DynamoDB', 'Neo4j', 'CouchDB', 'Firebase',
    'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'Git', 'CI/CD', 'Terraform',
    'Ansible', 'Puppet', 'Chef', 'Vagrant', 'Linux', 'Unix', 'Windows Server',
    'Machine Learning', 'Deep Learning', 'Artificial Intelligence', 'Data Science', 'Pandas',
    'NumPy', 'Scikit-learn', 'TensorFlow', 'PyTorch', 'Keras', 'OpenCV', 'NLP', 'Computer Vision',
    'Tableau', 'Power BI', 'Excel', 'Statistics', 'Data Analysis', 'Data Visualization',
    'Android', 'iOS', 'React Native', 'Flutter', 'Xamarin', 'Ionic', 'Cordova',
    'Project Management', 'Agile', 'Scrum', 'Kanban', 'Leadership', 'Team Management',
    'Strategic Planning', 'Business Analysis', 'Requirements Analysis', 'Stakeholder Management',
    'Risk Management', 'Budget Management', 'PMP', 'Six Sigma', 'Lean',
    'Digital Marketing', 'SEO', 'SEM', 'Social Media Marketing', 'Content Marketing',
    'Email Marketing', 'PPC', 'Google Analytics', 'Facebook Ads', 'LinkedIn Marketing',
    'Sales', 'Lead Generation', 'CRM', 'Salesforce', 'HubSpot',
    'UI/UX Design', 'Graphic Design', 'Photoshop', 'Illustrator', 'Figma', 'Sketch', 'Adobe XD',
    'InDesign', 'After Effects', 'Premiere Pro', 'Web Design', 'Logo Design',
    'Financial Analysis', 'Accounting', 'Bookkeeping', 'QuickBooks', 'SAP', 'Oracle Financials',
    'Financial Modeling', 'Budgeting', 'Forecasting', 'Tax Preparation', 'Audit',
    'Cybersecurity', 'Network Security', 'Penetration Testing', 'Ethical Hacking', 'Firewall',
    'VPN', 'Blockchain', 'IoT', 'Embedded Systems', 'Microcontrollers', 'Arduino', 'Raspberry Pi'
}

_VARIANT_MAP = {
    'ci cd': 'CI/CD', 'ci-cd': 'CI/CD', 'ci/cd': 'CI/CD',
    'rest api': 'REST API', 'rest apis': 'REST API', 'restful api': 'REST API',
    'ms excel': 'Excel', 'google analytics 4': 'Google Analytics',
}


def _normalize_token(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[\u2013\u2014\u2013\u2014]', '-', s)
    s = re.sub(r'[/\\]', '/', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return _VARIANT_MAP.get(s, s)


def _compile_skill_pattern(skill: str):
    tokens = re.split(r'\s+', skill.lower())
    sep = r'[ \u00A0/\-]*'
    pattern = r'\b' + sep.join(map(re.escape, tokens)) + r'\b'
    return re.compile(pattern, re.IGNORECASE)


# Pre-compiled patterns for all skills — built once at import time
_COMPILED_SKILL_PATTERNS = {s: _compile_skill_pattern(s) for s in _SKILLS_DATABASE}