pipeline {
    agent any

    environment {
        IMAGE_NAME    = 'aceest-fitness'
        IMAGE_TAG     = "${env.BUILD_NUMBER}"
        DOCKER_REPO   = 'snikhil2001/aceest-fitness'
        SONAR_PROJECT = 'nikku-nikhil_aceest-fitness'
        SONAR_ORG     = 'nikku-nikhil'
    }

    stages {

        // ── Stage 1: Checkout ────────────────────────────────────────────────
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/Nikku-Nikhil/aceest-fitness'
                echo "✅ Code checked out."
            }
        }

        // ── Stage 2: Install Dependencies ────────────────────────────────────
        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install flake8
                '''
            }
        }

        // ── Stage 3: Lint ────────────────────────────────────────────────────
        stage('Lint') {
            steps {
                sh '''
                    . venv/bin/activate
                    flake8 app.py --max-line-length=120 --select=E9,F63,F7,F82
                '''
                echo "✅ Lint passed."
            }
        }

        // ── Stage 4: Unit Tests + Coverage ───────────────────────────────────
        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest test_app.py -v --tb=short \
                        --junitxml=test-results.xml \
                        --cov=app --cov-report=xml
                '''
            }
            post {
                always { junit 'test-results.xml' }
            }
        }

        // ── Stage 5: SonarQube Analysis ──────────────────────────────────────
        // Requires: Jenkins → Manage Jenkins → Configure System → SonarQube
        //   Name: SonarCloud
        //   URL:  https://sonarcloud.io
        //   Auth: Add SonarCloud token as Jenkins Secret Text credential
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarCloud') {
                    sh '''
                        sonar-scanner \
                          -Dsonar.projectKey=${SONAR_PROJECT} \
                          -Dsonar.organization=${SONAR_ORG} \
                          -Dsonar.sources=app.py \
                          -Dsonar.tests=test_app.py \
                          -Dsonar.python.coverage.reportPaths=coverage.xml \
                          -Dsonar.host.url=https://sonarcloud.io
                    '''
                }
                echo "✅ SonarCloud scan submitted."
            }
        }

        // ── Stage 6: Quality Gate ─────────────────────────────────────────────
        // Waits for SonarCloud webhook to report pass/fail.
        // Configure webhook in SonarCloud: Administration → Webhooks
        //   URL: http://<jenkins-host>/sonarqube-webhook/
        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // ── Stage 7: Docker Build ─────────────────────────────────────────────
        stage('Docker Build') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_REPO}:${IMAGE_TAG}"
                sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${DOCKER_REPO}:latest"
                echo "✅ Docker image ${IMAGE_NAME}:${IMAGE_TAG} built and tagged."
            }
        }

        // ── Stage 8: Docker Smoke Test ────────────────────────────────────────
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

        // ── Stage 9: Push to Docker Hub ───────────────────────────────────────
        // Requires: Jenkins → Manage Credentials → Add
        //   Kind: Username with password
        //   ID:   docker-hub-credentials
        //   User: snikhil2001
        //   Pass: Docker Hub access token
        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'docker-hub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push ${DOCKER_REPO}:${IMAGE_TAG}
                        docker push ${DOCKER_REPO}:latest
                        docker logout
                    '''
                }
                echo "✅ Image snikhil2001/aceest-fitness:${IMAGE_TAG} pushed to Docker Hub."
            }
        }
    }

    post {
        success { echo "🏋️ BUILD SUCCEEDED – aceest-fitness:${IMAGE_TAG} is live on Docker Hub." }
        failure { echo "❌ BUILD FAILED – Check console output above." }
        always  { cleanWs() }
    }
}
