pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'python -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
                sh '. venv/bin/activate && pip install flake8 black mypy safety bandit'
            }
        }

        stage('Lint') {
            steps {
                sh '. venv/bin/activate && python -m black --check src/ tests/'
                sh '. venv/bin/activate && python -m flake8 src/ tests/'
                sh '. venv/bin/activate && python -m mypy src/'
            }
        }

        stage('Security') {
            steps {
                sh '. venv/bin/activate && python -m safety check'
                sh '. venv/bin/activate && python -m bandit -r src/'
            }
        }

        stage('Test') {
            steps {
                sh '. venv/bin/activate && python -m pytest'
            }
        }
    }
}
