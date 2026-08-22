pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'apt-get update && apt-get install -y python3 python3-pip python3-venv'
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
                sh '. venv/bin/activate && pip install flake8 black mypy bandit'
            }
        }

        stage('Code Quality') {
            parallel {
                stage('Lint') {
                    steps {
                        sh '. venv/bin/activate && black --check src/ tests/'
                        sh '. venv/bin/activate && flake8 src/ tests/'
                        sh '. venv/bin/activate && mypy src/'
                    }
                }

                stage('Security') {
                    steps {
                        sh '. venv/bin/activate && bandit -r src/'
                    }
                }

                stage('Test') {
                    steps {
                        sh '. venv/bin/activate && pytest --cov=src --cov-report=html --junitxml=report.xml 2>&1 | tee test-output.log'
                        sh '. venv/bin/activate && python classify.py test-output.log'
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
