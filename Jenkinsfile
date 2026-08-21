pipeline {
    agent any

    stages {
        stage('Code Quality') {
            parallel {
                stage('Lint') {
                    agent { docker { image 'python:3.12' } }
                    steps {
                        sh 'pip install flake8 black mypy'
                        sh 'black --check src/ tests/'
                        sh 'flake8 src/ tests/'
                        sh 'mypy src/'
                    }
                }

                stage('Security') {
                    agent { docker { image 'python:3.12' } }
                    steps {
                        sh 'pip install bandit'
                        sh 'bandit -r src/'
                    }
                }

                stage('Test') {
                    agent { docker { image 'python:3.12' } }
                    steps {
                        sh 'pip install -r requirements.txt'
                        sh 'pytest --cov=src --cov-report=term-missing'
                    }
                }
            }
        }
    }
}
