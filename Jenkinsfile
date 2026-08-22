pipeline {
    agent any

    stages {
        stage('Code Quality') {
            parallel {
                stage('Lint') {
                    agent {
                        docker {
                            image 'python:3.12'
                            args '-v /var/jenkins_home/workspace/sales-analyzer:/app -w /app --entrypoint=""'
                        }
                    }
                    options {
                        skipDefaultCheckout()
                    }
                    steps {
                        sh 'pip install flake8 black mypy'
                        sh 'black --check src/ tests/'
                        sh 'flake8 src/ tests/'
                        sh 'mypy src/'
                    }
                }

                stage('Security') {
                    agent {
                        docker {
                            image 'python:3.12'
                            args '-v /var/jenkins_home/workspace/sales-analyzer:/app -w /app --entrypoint=""'
                        }
                    }
                    options {
                        skipDefaultCheckout()
                    }
                    steps {
                        sh 'pip install bandit'
                        sh 'bandit -r src/'
                    }
                }

                stage('Test') {
                    agent {
                        docker {
                            image 'python:3.12'
                            args '-v /var/jenkins_home/workspace/sales-analyzer:/app -w /app --entrypoint=""'
                        }
                    }
                    options {
                        skipDefaultCheckout()
                    }
                    steps {
                        sh 'pip install -r requirements.txt'
                        sh 'pytest --cov=src --cov-report=html --junitxml=report.xml 2>&1 | tee test-output.log'
                        sh 'python classify.py test-output.log'
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'test-output.log', allowEmptyArchive: true
                            archiveArtifacts artifacts: 'htmlcov/**', allowEmptyArchive: true
                            archiveArtifacts artifacts: 'report.xml', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
    }
}