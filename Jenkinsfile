pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'python -m venv venv'
                sh 'venv\\Scripts\\activate && python -m pip install --upgrade pip'
                sh 'venv\\Scripts\\activate && pip install -r requirements.txt'
                sh 'venv\\Scripts\\activate && pip install flake8 black mypy bandit'
            }
        }

        stage('Code Quality') {
            parallel {
                agent { docker { image 'python:3.12' } }
                stage('Lint') {
                    steps {
                        sh 'venv\\Scripts\\activate && python -m black --check src/ tests/'
                        sh 'venv\\Scripts\\activate && python -m flake8 src/ tests/'
                        sh 'venv\\Scripts\\activate && python -m mypy src/'
                    }
                }

                stage('Security') {
                    agent { docker { image 'python:3.12' } }
                    steps {
                        sh 'venv\\Scripts\\activate && python -m bandit -r src/'
                    }
                }

                stage('Test') {
                    agent { docker { image 'python:3.12' } }
                    steps {
                        sh 'venv\\Scripts\\activate && python -m pytest --cov=src --cov-report=term-missing'
                    }
                }
            }
        }
    }
}
