pipeline {
    agent any
    options { timestamps() }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Clean Build Environment') {
            steps {
                sh 'rm -rf venv'
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }
        }
        stage('Lint') {
            steps { sh '. venv/bin/activate && flake8 app.py tests --max-line-length=120' }
        }
        stage('Unit Tests') {
            steps { sh '. venv/bin/activate && python -m pytest -v' }
        }
        stage('Docker Build') {
            steps { sh 'docker build -t aceest-fitness:${BUILD_NUMBER} .' }
        }
        stage('Test in Container') {
            steps { sh 'docker run --rm aceest-fitness:${BUILD_NUMBER} python -m pytest -q' }
        }
    }
    post {
        success { echo 'BUILD SUCCESS' }
        failure { echo 'BUILD FAILED' }
    }
}
