pipeline {
    agent any
    environment {
        py = "py"
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install dependencies') {
            steps {
                bat "${env.py} -m pip install --upgrade pip"
                bat "${env.py} -m pip install streamlit pandas"
            }
        }

        stage('Prepare Results Folder') {
            steps {
                bat "if exist Results rd /s /q Results"
                bat "mkdir Results"
            }
        }

        stage('Run Dashboard') {
            steps {
                bat "${env.py} -m streamlit run Dashboard/dashboard.py --server.headless true --server.fileWatcherType none &"
                bat "timeout /T 10"
            }
            post {
                always {
                    archiveArtifacts artifacts: 'Results/**', fingerprint: true
                }
            }
        }
    }
}
