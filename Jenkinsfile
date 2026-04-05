pipeline {
    agent any

    environment {
        IMAGE_NAME = 'aceest-fitness'
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/Nikku-Nikhil/aceest-fitness'
                echo "✅ Code checked out."
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    . venv/bin/activate
                    pip install flake8
                    flake8 app.py --max-line-length=120 --select=E9,F63,F7,F82
                '''
                echo "✅ Lint passed."
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest test_app.py -v --tb=short --junitxml=test-results.xml
                '''
            }
            post {
                always { junit 'test-results.xml' }
            }
        }

        stage('Docker Build') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                echo "✅ Docker image ${IMAGE_NAME}:${IMAGE_TAG} built."
            }
        }

        stage('Docker Smoke Test') {
            steps {
                sh '''
                    CID=$(docker run -d -p 5050:5000 ${IMAGE_NAME}:${IMAGE_TAG})
                    sleep 5
                    curl -f http://localhost:5050/health || (docker stop $CID && exit 1)
                    docker stop $CID
                '''
                echo "✅ Smoke test passed."
            }
        }
    }

    post {
        success { echo "🏋️ BUILD SUCCEEDED – ACEest image is ready." }
        failure { echo "❌ BUILD FAILED – Check console output." }
        always  { cleanWs() }
    }
}
