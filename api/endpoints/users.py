import logging
from web3 import Web3

from flask import request
from flask_restplus import Resource
# from rest_api_demo.api.blog.business import create_blog_post, update_post, delete_post
# from rest_api_demo.api.blog.serializers import blog_post, page_of_blog_posts
# from rest_api_demo.api.blog.parsers import pagination_arguments
from ..restplus import api
# from rest_api_demo.database.models import Post

log = logging.getLogger(__name__)

ns = api.namespace('user', description='Operations related to users')
# pagination_arguments.add_argument('bool', type=bool, required=False, default=1, help='Page number')
# pagination_arguments.add_argument('per_page', type=int, required=False, choices=[2, 10, 20, 30, 40, 50],
#                                   default=10, help='Results per page {error_msg}')

@ns.route('/list')
class User(Resource):

    # @api.expect(deploy_contract_request)
    # @api.marshal_with(page_of_blog_posts)
    def post(self):
        """
        Get list of all users
        """
        # per_page = args.get('per_page', 10)

        # posts_query = Post.query
        # posts_page = posts_query.paginate(page, per_page, error_out=False)

        # return posts_page

        w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        return w3.eth.accounts