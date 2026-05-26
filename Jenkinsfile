pipeline {
  agent any

  environment {
    IMAGE_NAME = 'store-app'
    REGISTRY = 'docker.io'
    DOCKERHUB_REPO = "${DOCKERHUB_USER}/${IMAGE_NAME}"
  }

<<<<<<< ours
  stages {
    stage('Checkout') { steps { checkout scm } }
=======
  options {
    timestamps()
    disableConcurrentBuilds()
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }
>>>>>>> theirs

    stage('Build Backend') {
      steps {
        sh 'cd backend && ./mvnw -DskipTests clean package'
      }
    }

    stage('Unit Tests') {
      steps {
        sh 'cd backend && ./mvnw test'
      }
    }

    stage('E2E Cypress') {
      steps {
        sh 'cd backend && npm ci && npm run cy:run'
      }
    }

    stage('Docker Build') {
      steps {
        sh 'docker build -t ${DOCKERHUB_REPO}:${BUILD_NUMBER} backend'
        sh 'docker tag ${DOCKERHUB_REPO}:${BUILD_NUMBER} ${DOCKERHUB_REPO}:latest'
      }
    }

    stage('Docker Push') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh 'echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin'
          sh 'docker push ${DOCKERHUB_REPO}:${BUILD_NUMBER}'
          sh 'docker push ${DOCKERHUB_REPO}:latest'
        }
      }
    }
  }
<<<<<<< ours
=======

  post {
    always {
      sh 'docker logout || true'
    }
  }
>>>>>>> theirs
}
