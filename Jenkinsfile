pipeline {
    agent any

    stages {
        stage('Code Quality') {
            parallel {
                stage('Lint') {
                    agent {
                        docker {
                            image 'python:3.12'
                            args '-v /var/jenkins_home/workspace/sales-analyzer:/app --entrypoint=""'
                        }
                    }
                    options {
                        skipDefaultCheckout()
                    }
                    steps {
                        sh 'pip install flake8 black mypy'
                        sh 'black --check /app/src/ /app/tests/'
                        sh 'flake8 /app/src/ /app/tests/'
                        sh 'mypy /app/src/'
                    }
                }

                stage('Security') {
                    agent {
                        docker {
                            image 'python:3.12'
                            args '-v /var/jenkins_home/workspace/sales-analyzer:/app --entrypoint=""'
                        }
                    }
                    options {
                        skipDefaultCheckout()
                    }
                    steps {
                        sh 'pip install bandit'
                        sh 'bandit -r /app/src/'
                    }
                }

                stage('Test') {
                    agent {
                        docker {
                            image 'python:3.12'
                            args '-v /var/jenkins_home/workspace/sales-analyzer:/app --entrypoint=""'
                        }
                    }
                    options {
                        skipDefaultCheckout()
                    }
                    steps {
                        sh 'pip install -r /app/requirements.txt'
                        sh 'cd /app && pytest --cov=src --cov-report=html --junitxml=report.xml 2>&1 | tee test-output.log'
                        sh 'cd /app && python classify.py test-output.log'
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: '/app/test-output.log', allowEmptyArchive: true
                            archiveArtifacts artifacts: '/app/htmlcov/**', allowEmptyArchive: true
                            archiveArtifacts artifacts: '/app/report.xml', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
    }
}
