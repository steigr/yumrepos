from __future__ import print_function
import json

from flask import Flask, request, abort, Blueprint, send_file


class Server(object):
    def __init__(self, backend):
        self.backend = backend
        self.app = Flask(__name__)
        self.allowed_extensions = set(['rpm'])

        self.add_admin_routes(backend)
        self.add_repos_routes(backend)

        # backend.update_all_metadata()

    def run(self, *args, **kwargs):
        self.app.run(*args, **kwargs)

    def add_repos_routes(self, backend):
        repos = Blueprint('repos', __name__)

        @repos.route('/', defaults={'path': ''})
        @repos.route('/<path:path>', methods=['GET'])
        def get_content(path):
            if backend.isfile(path):
                return send_file(backend.get_filename(path))
            if backend.exists(path):
                return (json.dumps(backend.list_rpms(path)), 200)
            return ('', 404)

        self.app.register_blueprint(repos, url_prefix='/repos')

    def add_admin_routes(self, backend):
        admin = Blueprint('admin', __name__)

        def allowed_file(filename):
            return '.' in filename and \
                filename.rsplit('.', 1)[1] in self.allowed_extensions

        @admin.route('/ready')
        def is_ready():
            return ('', 200)

        @admin.route('/update-all-metadata')
        def update_all_metadata():
            backend.update_all_metadata()
            return ('', 200)

        @admin.route('/repos/<path:reponame>', methods=['PUT'])
        def create_repo(reponame):
            print("create_repo %s" % reponame)
            if 'link_to' in request.args:
                link_to = request.args['link_to']
                if not backend.exists(link_to):
                    return ('%s not a repo' % link_to, 404)
                return backend.create_repo_link(reponame, link_to)
            return backend.create_repo(reponame)

        @admin.route('/repos/<path:reponame>', methods=['DELETE', 'DELETERECURSIVLY'])
        def remove_repo(reponame):
            if backend.is_link(reponame):
                return backend.remove_repo_link(reponame)
            recursivly = request.method == 'DELETERECURSIVLY'
            return backend.remove_repo(reponame, recursivly)

        @admin.route('/repos/<path:reponame>/update-metadata', methods=['GET'])
        def update_metadata(reponame):
            return backend.create_repo_metadata(reponame)

        @admin.route('/repos/<path:reponame>', methods=['POST'])
        def upload_rpm(reponame):
            file = request.files['rpm']
            if file and allowed_file(file.filename):
                return backend.upload_rpm(reponame, file)

            return "%s not a valid rpm" % file.filename, 400

        @admin.route('/repos/<reponame>/<rpmname>/stageto/<targetreponame>', methods=['PUT', 'STAGE'])
        def stage_rpm(reponame, rpmname, targetreponame):
            if not backend.exists(reponame, rpmname):
                return "rpm '%s/%s' does not exist" % (reponame, rpmname), 404
            if not backend.exists(targetreponame):
                return "target repo '%s' does not exist" % targetreponame, 404
            if backend.exists(targetreponame, rpmname):
                abort(409)
            return backend.stage(reponame, rpmname, targetreponame)

        @admin.route('/repos/<path:reponame>/<rpmname>/info', methods=['GET'])
        def get_rpm_info(reponame, rpmname):
            return (str(backend.get_rpm_info(reponame, rpmname)), 200)

        @admin.route('/repos/<path:reponame>/<rpmname>', methods=['DELETE'])
        def remove_rpm(reponame, rpmname):
            return backend.remove_rpm(reponame, rpmname)

        @admin.route('/repos/<path:reponame>/is_link', methods=['GET'])
        def is_repo_a_link(reponame):
            if backend.is_link(reponame):
                return ('true', 200)
            return ('false', 200)

        @admin.route('/shutdown', methods=['POST'])
        def shutdown():
            request.environ.get('werkzeug.server.shutdown')()
            return ('Shutdown NOW', 200)

        self.app.register_blueprint(admin, url_prefix='/admin')
