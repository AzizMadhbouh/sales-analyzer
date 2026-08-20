pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                bat 'python -m venv venv'
                bat 'venv\\Scripts\\activate && python -m pip install --upgrade pip'
                bat 'venv\\Scripts\\activate && pip install -r requirements.txt'
                bat 'venv\\Scripts\\activate && pip install flake8 black mypy safety bandit'
            }
        }
        stage('Code Quality') {
            parallel{
                stage('Lint') {
                    steps {
                        bat 'venv\\Scripts\\activate && python -m black --check src/ tests/'
                        bat 'venv\\Scripts\\activate && python -m flake8 src/ tests/'
                        bat 'venv\\Scripts\\activate && python -m mypy src/'
                    }
                }

                stage('Security') {
                    steps {
                        bat 'venv\\Scripts\\activate && python -m bandit -r src/'
                    }
                }

                stage('Test') {
                    steps {
                        bat 'venv\\Scripts\\activate && python -m pytest --cov=src --cov-report=term-missing'
                    }
                }
            }
        }
    }
}
