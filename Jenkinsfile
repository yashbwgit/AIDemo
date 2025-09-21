pipeline {
    agent any
    environment {
        PYTHONUNBUFFERED = 1
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Set up Python') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'which python3 || sudo apt-get update && sudo apt-get install -y python3 python3-pip'
                        sh 'python3 --version'
                    } else {
                        bat 'python --version'
                    }
                }
            }
        }
        stage('Install dependencies') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m pip install --upgrade pip'
                        sh 'python3 -m pip install streamlit pandas'
                    } else {
                        bat 'python -m pip install --upgrade pip'
                        bat 'python -m pip install streamlit pandas'
                    }
                }
            }
        }
        stage('Run Dashboard') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'streamlit run Vertexone/Dashboard/dashboard.py --server.headless true &'
                        sh 'sleep 10'
                    } else {
                        bat 'start /B streamlit run Vertexone/Dashboard/dashboard.py --server.headless true'
                        bat 'timeout /T 10'
                    }
                }
            }
        }
    }
    post {
        always {
            echo 'Pipeline completed.'
        }
    }
}
