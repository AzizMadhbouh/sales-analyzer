pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'apt-get update && apt-get install -y python3 python3-pip'
            }
        }

        stage('Code Quality') {
            parallel {
                stage('Lint') {
                    steps {
                        sh 'pip install flake8 black mypy'
                        sh 'black --check src/ tests/'
                        sh 'flake8 src/ tests/'
                        sh 'mypy src/'
                    }
                }

                stage('Security') {
                    steps {
                        sh 'pip install bandit'
                        sh 'bandit -r src/'
                    }
                }

                stage('Test') {
                    steps {
                        sh 'pip install -r requirements.txt'
                        sh 'pytest --cov=src --cov-report=html --junitxml=report.xml 2>&1 | tee test-output.log'
                        sh 'python3 classify.py test-output.log'
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
