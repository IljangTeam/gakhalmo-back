// Jenkinsfile for gakhalmo-back (FastAPI)
pipeline {
    agent none

    environment {
        OCIR_REGISTRY = 'yny.ocir.io'
        OCIR_NAMESPACE = 'axlgn2n9ijoa'
        IMAGE_NAME = 'gakhalmo/back'
        GITOPS_REPO = 'https://github.com/gakhalmo/gitops.git'
        GITOPS_CREDENTIALS = 'github-credentials'
    }

    stages {
        stage('Determine Environment') {
            agent any
            steps {
                script {
                    if (env.BRANCH_NAME == 'main') {
                        env.TARGET_ENV = 'prod'
                    } else if (env.BRANCH_NAME == 'develop') {
                        env.TARGET_ENV = 'dev'
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
                        if ! command -v kustomize &> /dev/null; then
                            curl -sLo /tmp/kustomize.tar.gz https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2Fv5.3.0/kustomize_v5.3.0_linux_arm64.tar.gz
                            tar -xzf /tmp/kustomize.tar.gz -C /tmp
                            chmod +x /tmp/kustomize
                            export PATH="/tmp:\$PATH"
                        fi

                        git clone https://\${GIT_USER}:\${GIT_TOKEN}@github.com/gakhalmo/gitops.git gitops-repo
                        cd gitops-repo/gakhalmo-back/overlay/${env.TARGET_ENV}

                        kustomize edit set image ${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}=${env.FULL_IMAGE}

                        cd ../../..
                        git config user.email "jenkins@klr.kr"
                        git config user.name "Jenkins CI"
                        git add .
                        git commit -m "chore: Update ${IMAGE_NAME} to ${env.IMAGE_TAG}" || echo "No changes to commit"
                        git push origin main
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
