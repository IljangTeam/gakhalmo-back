// Jenkinsfile for gakhalmo-back (FastAPI)
//
// 파이프라인 안전 장치(주의 사항):
//   1. disableConcurrentBuilds: Jenkins workspace 가 NFS 위에 마운트되므로
//      같은 브랜치 동시 실행 시 워크스페이스 충돌 + kaniko cache push 경합 발생 가능.
//      → 브랜치 단위 동시 실행을 원천 차단.
//   2. kaniko --cache-repo 를 env(dev|prod) 별로 완전히 분리.
//      dev/prod 파이프라인이 동시에 돌 때 같은 cache repo 에 write 하면
//      레이어 오염/불안정 캐시 hit 이 생긴다 (주로 prod 가 dev cache 를 물어오는 사고).
//   3. buildDiscarder: 오래된 빌드 아티팩트로 NFS 가 차는 걸 방지.
//   4. timeout: kaniko/git clone 이 네트워크 이슈로 hang 되는 빌드를 끊어낸다.

pipeline {
    agent none

    options {
        disableConcurrentBuilds()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '5'))
    }

    environment {
        OCIR_REGISTRY = 'yny.ocir.io'
        OCIR_NAMESPACE = 'axlgn2n9ijoa'
        IMAGE_NAME = 'gakhalmo/back'
        GITOPS_REPO = 'https://github.com/leestana01/gitops.git'
        GITOPS_CREDENTIALS = 'github-credentials'
    }

    stages {
        stage('Lint & Test') {
            agent {
                kubernetes {
                    label 'gakhalmo-back-py'
                    yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: python
      image: ghcr.io/astral-sh/uv:python3.14-bookworm-slim
      command: ['cat']
      tty: true
      resources:
        requests:
          cpu: '200m'
          memory: '512Mi'
        limits:
          cpu: '1000m'
          memory: '1Gi'
"""
                }
            }
            steps {
                // env 결정은 별도 stage(agent any)로 분리하면 k8s 기반 Jenkins 에
                // 매칭 executor 가 없어 hang 된다. pod 가 이미 뜬 현 stage 안에서
                // Groovy script 로 처리 — env 변수는 파이프라인 전역에 전파된다.
                script {
                    if (env.BRANCH_NAME == 'main') {
                        env.TARGET_ENV = 'prod'
                        env.GITOPS_KUSTOMIZE_DIR = 'apps/gakhalmo-back/overlays/prod'
                    } else if (env.BRANCH_NAME == 'develop') {
                        env.TARGET_ENV = 'dev'
                        env.GITOPS_KUSTOMIZE_DIR = 'apps/gakhalmo-back/overlays/dev'
                    } else {
                        error "Branch ${env.BRANCH_NAME} is not configured for deployment"
                    }
                    env.IMAGE_TAG = "${env.TARGET_ENV}-${env.BUILD_NUMBER}"
                    env.FULL_IMAGE = "${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}:${env.IMAGE_TAG}"
                    // env 별 cache repo 를 완전히 분리 — NFS 공유 환경에서 dev/prod 가
                    // 서로의 kaniko cache 를 덮어쓰지 않도록 한다.
                    env.KANIKO_CACHE_REPO = "${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}/cache/${env.TARGET_ENV}"

                    echo "TARGET_ENV=${env.TARGET_ENV}"
                    echo "IMAGE_TAG=${env.IMAGE_TAG}"
                    echo "KANIKO_CACHE_REPO=${env.KANIKO_CACHE_REPO}"
                }
                container('python') {
                    sh '''
                        set -eu
                        # asyncmy 0.2.11 은 Python 3.14 aarch64 휠을 제공하지 않아 sdist 빌드 폴백 →
                        # slim 이미지에 gcc 가 없어 실패한다. 빌드 툴체인만 최소 설치.
                        apt-get update -qq
                        apt-get install -y --no-install-recommends gcc libc6-dev
                        uv sync --frozen
                        uv run ruff check app tests alembic
                        uv run pytest -q
                    '''
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
                container('jnlp') {
                    sh """
                        /tools/kubectl exec -n jenkins \$(cat /etc/hostname) -c kaniko -- /kaniko/executor \\
                            --context=dir://\${WORKSPACE} \\
                            --dockerfile=\${WORKSPACE}/Dockerfile \\
                            --customPlatform=linux/arm64 \\
                            --destination=${env.FULL_IMAGE} \\
                            --destination=${OCIR_REGISTRY}/${OCIR_NAMESPACE}/${IMAGE_NAME}:${env.TARGET_ENV} \\
                            --cache=true \\
                            --cache-repo=${env.KANIKO_CACHE_REPO} \\
                            --cache-ttl=168h
                    """
                }
            }
        }

        stage('Update GitOps Repository') {
            agent {
                kubernetes {
                    label 'kaniko'
                }
            }
            steps {
                container('jnlp') {
                    withCredentials([usernamePassword(credentialsId: "${GITOPS_CREDENTIALS}", usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')]) {
                        // Token 은 http.extraheader 를 통해 base64 로 전달 — clone URL,
                        // git reflog, Jenkins console 어디에도 평문 노출되지 않는다.
                        // NFS 워크스페이스라 이전 빌드의 gitops-repo 가 남아있을 수 있어
                        // clone 전에 강제 삭제 — "destination path already exists" 방지.
                        sh '''
                            set +x
                            rm -rf gitops-repo
                            GIT_AUTH_HEADER="Authorization: Basic $(printf '%s:%s' "$GIT_USER" "$GIT_TOKEN" | base64 | tr -d '\\n')"
                            git -c http.extraheader="$GIT_AUTH_HEADER" \\
                                clone https://github.com/leestana01/gitops.git gitops-repo
                        '''
                        sh """
                            set +x
                            GIT_AUTH_HEADER="Authorization: Basic \$(printf '%s:%s' "\$GIT_USER" "\$GIT_TOKEN" | base64 | tr -d '\\n')"
                            cd gitops-repo
                            sed -i "s|newTag:.*|newTag: ${env.IMAGE_TAG}|" ${env.GITOPS_KUSTOMIZE_DIR}/kustomization.yaml

                            git config user.email "jenkins@klr.kr"
                            git config user.name "Jenkins CI"
                            git add ${env.GITOPS_KUSTOMIZE_DIR}/kustomization.yaml
                            git commit -m "update ${IMAGE_NAME} to ${env.IMAGE_TAG}" || echo "No changes to commit"
                            git -c http.extraheader="\$GIT_AUTH_HEADER" push origin HEAD:main
                        """
                    }
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
