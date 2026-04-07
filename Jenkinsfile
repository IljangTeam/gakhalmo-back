// Jenkinsfile for gakhalmo-back (FastAPI)
pipeline {
    agent none

    environment {
        OCIR_REGISTRY = 'yny.ocir.io'
        OCIR_NAMESPACE = 'axlgn2n9ijoa'
        IMAGE_NAME = 'gakhalmo/back'
        GITOPS_REPO = 'https://github.com/leestana01/gitops.git'
        GITOPS_CREDENTIALS = 'github-credentials'
    }

    stages {
        stage('Determine Environment') {
            agent any
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        env.TARGET_ENV = 'prod'
                        env.GITOPS_DEPLOYMENT_PATH = 'apps/gakhalmo-back/base/deployment.yaml'
                    } else if (env.BRANCH_NAME == 'develop') {
                        env.TARGET_ENV = 'dev'
                        env.GITOPS_DEPLOYMENT_PATH = 'apps/gakhalmo-back-dev/base/deployment.yaml'
                    } else {
                        error "Branch ${env.BRANCH_NAME} is not configured for deployment"
                    }
                    env.IMAGE_TAG = "${env.TARGET_ENV}-${env.BUILD_NUMBER}"
                    env.FULL_IMAGE = "${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}:${env.IMAGE_TAG}"
                }
            }
        }

        stage('Build & Push Docker Image') {
            agent {
                kubernetes {
                    label 'kaniko'
                }
            }
            steps {
                container('kaniko') {
                    sh """
                        /kaniko/executor \\
                            --context=dir://\${WORKSPACE} \\
                            --dockerfile=\${WORKSPACE}/Dockerfile \\
                            --destination=${env.FULL_IMAGE} \\
                            --destination=${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}:${env.TARGET_ENV} \\
                            --customPlatform=linux/arm64 \\
                            --cache=true \\
                            --cache-repo=${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}/cache
                    """
                }
            }
        }

        stage('Update GitOps Repository') {
            agent any
            steps {
                withCredentials([usernamePassword(credentialsId: "${GITOPS_CREDENTIALS}", usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')]) {
                    sh """
                        git clone https://\${GIT_USER}:\${GIT_TOKEN}@github.com/leestana01/gitops.git gitops-repo
                        cd gitops-repo

                        sed -i "s|image: ${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}:.*|image: ${env.FULL_IMAGE}|" ${env.GITOPS_DEPLOYMENT_PATH}

                        git config user.email "jenkins@klr.kr"
                        git config user.name "Jenkins CI"
                        git add ${env.GITOPS_DEPLOYMENT_PATH}
                        git commit -m "chore: Update ${IMAGE_NAME} to ${env.IMAGE_TAG}" || echo "No changes to commit"
                        git push origin HEAD:main
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Successfully deployed ${IMAGE_NAME}:${env.IMAGE_TAG} to ${env.TARGET_ENV}"
        }
        failure {
            echo "Pipeline failed for ${IMAGE_NAME}"
        }
    }
}
