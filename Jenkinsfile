pipeline {
    agent any

    stages {
        stage('Setup') {
            steps {
                sh 'apt-get update && apt-get install -y python3 python3-pip python3-venv'
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
                sh '. venv/bin/activate && pip install flake8 black mypy bandit scikit-learn'
            }
        }

        stage('Code Quality') {
            steps {
                sh '. venv/bin/activate && black --check src/ tests/ 2>&1 | tee -a build-output.log'
                sh '. venv/bin/activate && flake8 src/ tests/ 2>&1 | tee -a build-output.log'
                sh '. venv/bin/activate && mypy src/ 2>&1 | tee -a build-output.log'
                sh '. venv/bin/activate && bandit -r src/ 2>&1 | tee -a build-output.log'
                sh '. venv/bin/activate && pytest --cov=src --cov-report=html --junitxml=report.xml 2>&1 | tee -a build-output.log'
                sh '. venv/bin/activate && python predict.py build-output.log > analysis-report.txt'
            }
            post {
                always {
                    archiveArtifacts artifacts: 'build-output.log', allowEmptyArchive: true
                    archiveArtifacts artifacts: 'htmlcov/**', allowEmptyArchive: true
                    archiveArtifacts artifacts: 'report.xml', allowEmptyArchive: true
                    archiveArtifacts artifacts: 'analysis-report.txt', allowEmptyArchive: true
                }
            }
        }
    }
}
