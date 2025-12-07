"""模型管理相关API接口

本模块提供了完整的模型供应商和模型管理功能，包括：
- 模型供应商的增删改查操作
- 模型的增删改查操作
- 供应商logo上传功能
- 默认模型设置功能
- 数据验证和错误处理

技术栈：
- FastAPI：提供RESTful API接口
- SQLAlchemy：数据库ORM操作
- SQLite：轻量级数据库存储

设计特点：
- 采用模块化架构，与业务逻辑分离
- 支持文件上传，处理供应商logo
- 实现数据完整性验证
- 提供友好的错误提示
- 支持分页查询

注意事项：
- 当前使用MockUser替代真实用户认证，便于测试
- 文件上传支持多种图片格式
- 数据库操作包含完整的事务处理
- API端点前缀为/model-management（在v1路由中配置）
"""
# 标准库导入
from typing import Any, List, Optional  # 类型提示支持
from datetime import datetime  # 日期时间处理
import os  # 文件系统操作
import uuid  # 唯一ID生成

# FastAPI框架导入
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form  # FastAPI核心组件
from fastapi.responses import JSONResponse  # 自定义响应类型

# SQLAlchemy数据库导入
from sqlalchemy.orm import Session  # 数据库会话
from sqlalchemy.exc import IntegrityError  # 数据库完整性错误
from sqlalchemy import create_engine  # 数据库引擎创建
from sqlalchemy.orm import sessionmaker  # 会话工厂

# 应用内部导入
from app.models.model_management import ModelSupplier, Model  # 数据库模型

# 核心依赖
from app.core.dependencies import get_db  # 数据库依赖获取函数

# 数据验证模型（Pydantic schemas）
from app.modules.supplier_model_management.schemas.model_management import (
    ModelSupplierCreate,    # 供应商创建请求模型
    ModelSupplierUpdate,    # 供应商更新请求模型
    ModelSupplierResponse,  # 供应商响应模型
    ModelCreate,            # 模型创建请求模型
    ModelUpdate,            # 模型更新请求模型
    ModelResponse,          # 模型响应模型
    ModelSupplierListResponse,  # 供应商列表响应模型
    ModelListResponse,          # 模型列表响应模型
    SetDefaultModelRequest      # 设置默认模型请求模型
)

# ======================================
# 文件上传配置
# ======================================

# 创建上传目录
# 使用多层os.path.dirname获取项目根目录
# 路径：backend/app/frontend/public/logos/providers
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "../frontend/public/logos/providers")
UPLOAD_DIR = os.path.normpath(UPLOAD_DIR)  # 规范化路径，解决相对路径问题
os.makedirs(UPLOAD_DIR, exist_ok=True)  # 确保目录存在，不存在则创建
print(f"文件上传目录: {UPLOAD_DIR}")  # 调试日志，输出实际上传目录

# 支持的图片扩展名集合
# 限制为常见的图片格式，确保安全和兼容性
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# 模拟用户类声明（用于开发测试，替代真实认证）
# 实际项目中应替换为真实的用户认证系统


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否在允许列表中
    
    Args:
        filename: 上传的文件名
        
    Returns:
        bool: 如果文件扩展名允许返回True，否则返回False
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


async def save_upload_file(upload_file: UploadFile) -> Optional[str]:
    """保存上传的文件并返回文件路径
    
    处理步骤：
    1. 验证文件扩展名
    2. 验证文件名完整性
    3. 生成唯一文件名（避免覆盖）
    4. 保存文件到指定目录
    5. 返回文件路径
    
    Args:
        upload_file: FastAPI UploadFile对象
        
    Returns:
        Optional[str]: 保存后的文件相对路径，失败则返回None
        
    Raises:
        HTTPException: 如果文件类型不允许或文件名无效
    """
    # 检查文件扩展名是否允许
    if not allowed_file(upload_file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型，请上传图片文件 (png, jpg, jpeg, gif, webp)"
        )
    
    # 验证文件名完整性
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空"
        )
    
    # 检查文件名是否包含扩展名
    if '.' not in upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名必须包含扩展名"
        )
    # 提取文件扩展名
    file_ext = upload_file.filename.rsplit('.', 1)[1].lower()
    
    # 生成唯一文件名：时间戳 + 微秒 + 扩展名
    # 格式：YYYYMMDD_HHMMSS_ffffff.ext
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)  # 完整文件路径
    
    try:
        print(f"尝试保存文件到: {file_path}")  # 调试日志
        
        # 异步读取文件内容并保存
        # 使用with语句确保文件正确关闭
        with open(file_path, "wb") as buffer:
            content = await upload_file.read()  # 异步读取文件内容
            buffer.write(content)  # 写入文件
        
        print(f"文件保存成功: {unique_filename}")  # 成功日志
        
        # 返回相对路径（前端可访问）
        return unique_filename
        
    except Exception as e:
        print(f"文件保存失败: {str(e)}")  # 错误日志
        # 保存失败抛出内部服务器错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}"
        )


# ======================================
# 开发测试配置
# ======================================

# 临时注释掉真实认证依赖以方便开发测试
# 实际部署时应取消注释并使用真实认证系统
# from app.api.deps import get_current_active_superuser
# from app.models.user import User


# 模拟用户类
# 用于开发环境测试，替代真实用户认证
# 包含与真实用户模型兼容的基本属性
class MockUser:
    """模拟用户类（开发测试用）"""
    def __init__(self):
        self.id = 1  # 默认用户ID
        self.is_active = True  # 用户状态为激活
        self.is_superuser = True  # 用户为超级管理员


def get_mock_user() -> MockUser:
    """获取模拟用户实例
    
    Returns:
        MockUser: 模拟用户对象，用于开发测试
    """
    return MockUser()


# ======================================
# API路由配置
# ======================================

# 创建API路由器实例
# 该路由器将被包含在主API中
router = APIRouter()


# ======================================
# 模型供应商管理API
# ======================================

@router.post("/suppliers", summary="创建模型供应商", response_model=ModelSupplierResponse)
async def create_model_supplier(
    name: str = Form(...),  # 供应商名称（必填）
    description: Optional[str] = Form(None),  # 供应商描述
    api_endpoint: Optional[str] = Form(None),  # API调用端点
    api_key_required: Optional[bool] = Form(False),  # 是否需要API密钥认证
    is_active: bool = Form(True),  # 是否激活该供应商
    logo: Optional[UploadFile] = File(None),  # 供应商logo图片
    category: Optional[str] = Form(None),  # 供应商类别
    website: Optional[str] = Form(None),  # 供应商官方网站
    api_docs: Optional[str] = Form(None),  # API文档链接
    api_key: Optional[str] = Form(None),  # API密钥（如果需要）
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    创建新的模型供应商（支持图片上传功能）
    
    功能说明：
    - 创建新的模型供应商记录
    - 支持上传供应商logo图片
    - 自动生成创建时间和更新时间
    - 验证供应商名称唯一性
    - 处理文件上传和保存
    
    参数详解：
    - name: 供应商名称，必须唯一
    - description: 供应商详细描述
    - api_endpoint: 模型API的调用地址
    - api_key_required: 调用该供应商API是否需要密钥
    - is_active: 供应商是否处于激活状态
    - logo: 供应商的logo图片文件（支持png/jpg/jpeg/gif/webp）
    - category: 供应商所属类别
    - website: 供应商官方网站链接
    - api_docs: 供应商API文档链接
    - api_key: 调用API所需的密钥（如果需要）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - 返回创建的供应商完整信息，包括ID、名称、描述、状态等
    - 包含保存后的logo文件路径
    
    异常处理：
    - 400 Bad Request: 供应商名称已存在
    - 400 Bad Request: 输入数据违反完整性约束
    - 500 Internal Server Error: 文件上传失败
    """
    try:
        # 1. 检查供应商名称是否已存在
        existing_supplier = db.query(ModelSupplier).filter(
            ModelSupplier.name == name
        ).first()
        
        if existing_supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="供应商名称已存在，请使用其他名称"
            )
        
        # 2. 处理logo图片上传
        logo_url = None
        if logo:
            logo_url = await save_upload_file(logo)  # 调用文件保存函数
        
        # 3. 创建供应商数据对象
        now = datetime.utcnow()  # 使用UTC时间确保一致性
        db_supplier = ModelSupplier(
            name=name,
            description=description,
            api_endpoint=api_endpoint,
            api_key_required=api_key_required,
            is_active=is_active,
            logo=logo_url,
            category=category,
            website=website,
            api_docs=api_docs,
            api_key=api_key,
            created_at=now,  # 创建时间
            updated_at=now   # 更新时间
        )
        
        # 4. 保存到数据库
        db.add(db_supplier)  # 添加到会话
        db.commit()  # 提交事务
        db.refresh(db_supplier)  # 刷新获取最新数据
        
        # 5. 构建响应数据
        # 使用name作为display_name，保持字段一致性
        return {
            "id": db_supplier.id,
            "name": db_supplier.name,
            "display_name": db_supplier.name,  # 显示名称与供应商名称相同
            "description": db_supplier.description,
            "api_endpoint": db_supplier.api_endpoint,
            "api_key_required": db_supplier.api_key_required,
            "is_active": db_supplier.is_active,
            "logo": db_supplier.logo,
            "category": db_supplier.category,
            "website": db_supplier.website,
            "api_docs": db_supplier.api_docs,
            "api_key": db_supplier.api_key,
            "created_at": db_supplier.created_at,
            "updated_at": db_supplier.updated_at
        }
        
    except IntegrityError as e:
        # 处理数据库完整性错误（如唯一约束、外键约束等）
        db.rollback()  # 回滚事务
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="创建供应商失败，请检查输入数据是否符合要求"
        )


@router.get("/suppliers", summary="获取模型供应商列表", response_model=ModelSupplierListResponse)
async def get_model_suppliers(
    skip: int = 0,  # 分页：跳过的记录数，默认为0
    limit: int = 100,  # 分页：返回的最大记录数，默认为100
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    获取模型供应商列表（支持分页）
    
    功能说明：
    - 查询所有模型供应商记录，包括非激活状态的供应商
    - 支持分页查询，通过skip和limit参数控制
    - 为每个供应商添加display_name字段
    - 返回标准的分页响应格式
    
    参数详解：
    - skip: 从第几条记录开始返回（0表示从第一条开始）
    - limit: 最多返回多少条记录（默认100条）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - ModelSupplierListResponse对象，包含：
      - suppliers: 供应商列表（包含display_name字段）
      - total: 总记录数
    
    设计说明：
    - 使用offset和limit实现分页查询，适合中小规模数据
    - 为每个供应商添加display_name字段，确保前端显示一致
    - 返回标准的响应模型，便于前端处理
    """
    # 1. 执行分页查询，获取供应商列表
    suppliers = db.query(ModelSupplier).offset(skip).limit(limit).all()
    
    # 2. 获取总记录数，用于分页信息
    total = db.query(ModelSupplier).count()
    
    # 3. 为每个供应商添加display_name字段
    suppliers_with_display_name = []
    for supplier in suppliers:
        # 创建包含display_name字段的供应商字典
        supplier_dict = {
            "id": supplier.id,
            "name": supplier.name,
            "display_name": supplier.name,  # 使用name作为默认display_name
            "description": supplier.description,
            "api_endpoint": supplier.api_endpoint,
            "api_key_required": supplier.api_key_required,
            "is_active": supplier.is_active,
            "logo": supplier.logo,
            "category": supplier.category,
            "website": supplier.website,
            "api_docs": supplier.api_docs,
            "api_key": supplier.api_key,
            "created_at": supplier.created_at,
            "updated_at": supplier.updated_at
        }
        suppliers_with_display_name.append(supplier_dict)
    
    # 4. 返回标准化的分页响应
    return ModelSupplierListResponse(
        suppliers=suppliers_with_display_name,
        total=total
    )


@router.get("/suppliers/{supplier_id}", summary="获取单个模型供应商", response_model=ModelSupplierResponse)
async def get_model_supplier(
    supplier_id: int,  # 路径参数：供应商ID
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    根据ID获取指定的模型供应商信息
    
    功能说明：
    - 通过供应商ID查询单个供应商的详细信息
    - 验证供应商是否存在
    - 返回标准化的供应商响应数据
    
    参数详解：
    - supplier_id: 供应商的唯一标识符（路径参数）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - ModelSupplierResponse对象，包含供应商的完整信息
    
    异常处理：
    - 404 Not Found: 如果指定ID的供应商不存在
    
    实现说明：
    - 使用filter条件精确查询指定ID的供应商
    - 只返回第一个匹配的结果（ID唯一）
    - 如果查询结果为空，抛出404异常
    """
    # 1. 根据ID查询供应商
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    
    # 2. 验证供应商是否存在
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{supplier_id}的供应商不存在"
        )
    
    # 3. 返回供应商信息
    return supplier


@router.put("/suppliers/{supplier_id}", summary="更新模型供应商信息", status_code=status.HTTP_200_OK)
async def update_model_supplier(
    supplier_id: int,  # 路径参数：供应商ID
    name: Optional[str] = Form(None),  # 表单参数：供应商名称（可选）
    description: Optional[str] = Form(None),  # 表单参数：供应商描述（可选）
    api_endpoint: Optional[str] = Form(None),  # 表单参数：API端点（可选）
    api_key_required: Optional[bool] = Form(None),  # 表单参数：是否需要API密钥（可选）
    is_active: Optional[bool] = Form(None),  # 表单参数：是否激活（可选）
    logo: Optional[UploadFile] = File(None),  # 文件参数：供应商logo图片（可选）
    existing_logo: Optional[str] = Form(None),  # 表单参数：现有logo路径（可选）
    category: Optional[str] = Form(None),  # 表单参数：供应商类别（可选）
    website: Optional[str] = Form(None),  # 表单参数：供应商网站（可选）
    api_docs: Optional[str] = Form(None),  # 表单参数：API文档链接（可选）
    api_key: Optional[str] = Form(None),  # 表单参数：API密钥（可选）
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    更新模型供应商信息（支持图片上传）
    
    功能说明：
    - 支持部分字段更新，未提供的字段保持不变
    - 支持上传新的logo图片或保留现有logo
    - 自动更新修改时间戳
    - 提供完整的错误处理和验证
    
    参数详解：
    - supplier_id: 要更新的供应商ID（路径参数）
    - name: 供应商名称（可选，更新时会检查唯一性）
    - description: 供应商描述（可选）
    - api_endpoint: API端点URL（可选）
    - api_key_required: 是否需要API密钥进行访问（可选）
    - is_active: 是否激活该供应商（可选）
    - logo: 新的logo图片文件（可选，与existing_logo二选一）
    - existing_logo: 现有logo的路径（可选，当不上传新logo时使用）
    - category: 供应商类别（可选）
    - website: 供应商官方网站（可选）
    - api_docs: API文档链接（可选）
    - api_key: API访问密钥（可选，敏感信息）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - 包含更新后供应商完整信息的字典，包括display_name字段
    
    异常处理：
    - 404 Not Found: 如果指定ID的供应商不存在
    - 400 Bad Request: 如果供应商名称重复或输入数据无效
    """
    # 1. 根据ID查询供应商
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    
    # 2. 验证供应商是否存在
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{supplier_id}的供应商不存在"
        )
    
    # 3. 检查名称是否重复（如果更新了名称）
    if name and name != supplier.name:
        existing_supplier = db.query(ModelSupplier).filter(
            ModelSupplier.name == name
        ).first()
        if existing_supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"名称为'{name}'的供应商已存在"
            )
    
    # 4. 更新提供的字段
    if name is not None:
        setattr(supplier, 'name', name)
    if description is not None:
        setattr(supplier, 'description', description)
    if api_endpoint is not None:
        setattr(supplier, 'api_endpoint', api_endpoint)
    if api_key_required is not None:
        setattr(supplier, 'api_key_required', api_key_required)
    if is_active is not None:
        setattr(supplier, 'is_active', is_active)
    if category is not None:
        setattr(supplier, 'category', category)
    if website is not None:
        setattr(supplier, 'website', website)
    if api_docs is not None:
        setattr(supplier, 'api_docs', api_docs)
    if api_key is not None:
        setattr(supplier, 'api_key', api_key)
    
    # 5. 处理logo图片
    if logo:
        # 如果有新的logo文件上传，保存它并更新供应商logo路径
        logo_path = await save_upload_file(logo)
        setattr(supplier, 'logo', logo_path)
        print(f"已更新供应商{supplier_id}的logo为新上传的文件: {logo_path}")
    elif existing_logo is not None:
        # 如果提供了existing_logo，使用它更新供应商logo路径
        setattr(supplier, 'logo', existing_logo)
        print(f"已为供应商{supplier_id}保留现有logo: {supplier.logo}")
    # 否则，保持原有logo不变
    
    # 6. 更新修改时间戳
    setattr(supplier, 'updated_at', datetime.utcnow())
    
    try:
        # 7. 提交数据库事务
        db.commit()
        
        # 8. 刷新数据库会话以获取最新数据
        db.refresh(supplier)
        
        # 9. 返回响应 - 构建标准化的供应商信息
        return {
            "id": supplier.id,
            "name": supplier.name,
            "display_name": supplier.name,  # 使用name作为display_name
            "description": supplier.description,
            "api_endpoint": supplier.api_endpoint,
            "api_key_required": supplier.api_key_required,
            "is_active": supplier.is_active,
            "logo": supplier.logo,
            "category": supplier.category,
            "website": supplier.website,
            "api_docs": supplier.api_docs,
            "api_key": supplier.api_key,
            "created_at": supplier.created_at,
            "updated_at": supplier.updated_at
        }
    except IntegrityError:
        # 10. 处理数据库完整性错误
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新供应商失败，请检查输入数据的有效性和完整性"
        )


@router.delete("/suppliers/{supplier_id}", summary="删除模型供应商", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_supplier(
    supplier_id: int,  # 路径参数：供应商ID
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> None:
    """
    删除指定的模型供应商
    
    功能说明：
    - 删除指定ID的模型供应商
    - 先检查供应商是否存在
    - 验证供应商是否有相关联的模型
    - 如果有相关模型，则不允许删除
    - 成功删除后返回204 No Content状态码
    
    参数详解：
    - supplier_id: 要删除的供应商ID（路径参数）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - 无内容，返回204 No Content状态码
    
    异常处理：
    - 404 Not Found: 如果指定ID的供应商不存在
    - 400 Bad Request: 如果供应商有相关联的模型，需要先删除模型
    """
    # 1. 记录删除请求日志
    print(f"收到删除供应商请求，供应商ID: {supplier_id}")
    
    # 2. 根据ID查询供应商
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    
    # 3. 验证供应商是否存在
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{supplier_id}的供应商不存在"
        )
    
    # 4. 检查供应商是否有相关联的模型
    # 使用直接查询方式替代关系属性访问，避免关系定义问题
    has_models = db.query(Model).filter(Model.supplier_id == supplier_id).first() is not None
    
    # 5. 如果有相关模型，不允许删除
    if has_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法删除包含模型的供应商，请先删除该供应商下的所有模型"
        )
    
    # 6. 执行删除操作
    db.delete(supplier)
    
    # 7. 提交数据库事务
    db.commit()
    
    # 注意：由于使用了204状态码，函数返回None（无内容）


# 模型管理相关路由
@router.post("/suppliers/{supplier_id}/models", summary="创建新模型", response_model=ModelResponse)
async def create_model(
    supplier_id: int,  # 路径参数：供应商ID
    model: ModelCreate,  # 请求体：模型创建数据
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    为指定供应商创建新模型
    
    功能说明：
    - 为指定供应商创建新的AI模型
    - 验证供应商是否存在
    - 处理默认模型逻辑：
      - 如果新模型设置为默认模型，自动将其他模型的is_default设置为False
      - 如果是该供应商的第一个模型，自动设为默认模型
    - 提供完整的错误处理
    
    参数详解：
    - supplier_id: 供应商ID（路径参数）
    - model: 模型创建数据，包含模型名称、描述、参数等信息
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - 创建的模型信息，包含完整的模型属性
    
    异常处理：
    - 404 Not Found: 如果指定ID的供应商不存在
    - 400 Bad Request: 如果输入数据无效或违反数据库约束
    """
    # 1. 验证供应商是否存在
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{supplier_id}的供应商不存在"
        )
    
    # 2. 确保supplier_id一致
    model_data = model.model_dump()  # 将Pydantic模型转换为字典
    model_data['supplier_id'] = supplier_id  # 确保使用路径参数中的供应商ID
    
    try:
        # 3. 创建新模型
        db_model = Model(**model_data)  # 使用字典数据创建模型实例
        db.add(db_model)  # 添加到数据库会话
        
        # 4. 处理默认模型逻辑
        if db_model.is_default is True:
            # 4.1 如果新模型设置为默认，将其他模型的is_default设置为False
            db.query(Model).filter(
                Model.supplier_id == supplier_id,  # 同一供应商
                Model.id != db_model.id  # 排除当前模型
            ).update({Model.is_default: False})  # 批量更新
        elif db.query(Model).filter(Model.supplier_id == supplier_id).count() == 0:
            # 4.2 如果是该供应商的第一个模型，自动设为默认
            setattr(db_model, 'is_default', True)
        
        # 5. 提交数据库事务
        db.commit()
        
        # 6. 刷新数据库会话以获取最新数据
        db.refresh(db_model)
        
        # 7. 返回创建的模型信息
        return db_model
    except IntegrityError:
        # 8. 处理数据库完整性错误
        db.rollback()  # 回滚事务
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="创建模型失败，请检查输入数据的有效性和完整性"
        )


@router.get("/suppliers/{supplier_id}/models", summary="获取供应商模型列表", response_model=ModelListResponse)
async def get_models(
    supplier_id: int,  # 路径参数：供应商ID
    skip: int = 0,  # 查询参数：跳过的记录数，用于分页
    limit: int = 100,  # 查询参数：返回的最大记录数，默认100
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    获取指定供应商的模型列表，支持分页
    
    功能说明：
    - 获取指定供应商的所有模型信息
    - 支持分页查询，通过skip和limit参数控制
    - 验证供应商是否存在
    - 构建标准化的模型响应列表
    - 返回包含模型列表和总数的响应
    
    参数详解：
    - supplier_id: 供应商ID（路径参数）
    - skip: 跳过的记录数，用于实现分页，默认0
    - limit: 返回的最大记录数，用于实现分页，默认100
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - ModelListResponse对象，包含模型列表和总数
      - models: 模型响应列表
      - total: 模型总数
    
    异常处理：
    - 404 Not Found: 如果指定ID的供应商不存在
    """
    # 1. 验证供应商是否存在
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{supplier_id}的供应商不存在"
        )
    
    # 2. 查询模型列表（带分页）
    models = db.query(Model).filter(
        Model.supplier_id == supplier_id
    ).offset(skip).limit(limit).all()
    
    # 3. 查询模型总数
    total = db.query(Model).filter(Model.supplier_id == supplier_id).count()
    
    # 4. 构建模型响应列表
    model_responses = [
        ModelResponse(
            id=model.id,
            name=model.name,
            display_name=getattr(model, "display_name", model.name),  # 如果没有display_name，使用name
            description=model.description,
            supplier_id=model.supplier_id,
            context_window=model.context_window,
            max_tokens=getattr(model, "max_tokens", None),  # 兼容可能没有max_tokens的模型
            is_default=model.is_default,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
        for model in models  # 遍历所有查询到的模型
    ]
    
    # 5. 返回模型列表响应
    return ModelListResponse(
        models=model_responses,  # 模型响应列表
        total=total  # 模型总数
    )


@router.get("/suppliers/{supplier_id}/models/{model_id}", summary="获取单个模型信息", response_model=ModelResponse)
async def get_model(
    supplier_id: int,  # 路径参数：供应商ID
    model_id: int,  # 路径参数：模型ID
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    根据供应商ID和模型ID获取指定模型的详细信息
    
    功能说明：
    - 获取指定供应商下的特定模型信息
    - 同时验证供应商ID和模型ID，确保资源访问的安全性
    - 构建标准化的模型响应数据
    
    参数详解：
    - supplier_id: 供应商ID（路径参数）
    - model_id: 模型ID（路径参数）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - ModelResponse对象，包含模型的完整信息
    
    异常处理：
    - 404 Not Found: 如果指定的模型不存在，或不属于指定的供应商
    """
    # 1. 根据供应商ID和模型ID查询模型
    model = db.query(Model).filter(
        Model.id == model_id,  # 匹配模型ID
        Model.supplier_id == supplier_id  # 同时匹配供应商ID，确保资源安全
    ).first()
    
    # 2. 验证模型是否存在
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{model_id}的模型不存在于ID为{supplier_id}的供应商下"
        )
    
    # 3. 返回模型信息
    return model


@router.put("/suppliers/{supplier_id}/models/{model_id}", summary="更新模型信息", response_model=ModelResponse)
async def update_model(
    supplier_id: int,  # 路径参数：供应商ID
    model_id: int,  # 路径参数：模型ID
    model_update: ModelUpdate,  # 请求体：模型更新数据
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    更新指定模型的信息
    
    功能说明：
    - 更新指定供应商下的特定模型信息
    - 支持部分字段更新，未提供的字段保持不变
    - 处理默认模型逻辑：如果将模型设置为默认，自动将其他模型的is_default设置为False
    - 提供完整的错误处理
    
    参数详解：
    - supplier_id: 供应商ID（路径参数）
    - model_id: 模型ID（路径参数）
    - model_update: 模型更新数据，包含需要修改的字段
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - 更新后的ModelResponse对象
    
    异常处理：
    - 404 Not Found: 如果指定的模型不存在，或不属于指定的供应商
    - 400 Bad Request: 如果输入数据无效或违反数据库约束
    """
    # 1. 根据供应商ID和模型ID查询模型
    model = db.query(Model).filter(
        Model.id == model_id,  # 匹配模型ID
        Model.supplier_id == supplier_id  # 同时匹配供应商ID，确保资源安全
    ).first()
    
    # 2. 验证模型是否存在
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{model_id}的模型不存在于ID为{supplier_id}的供应商下"
        )
    
    # 3. 获取更新数据（排除未设置的字段）
    update_data = model_update.model_dump(exclude_unset=True)  # 只获取实际提供的更新字段
    
    # 4. 处理默认模型逻辑
    if 'is_default' in update_data and update_data['is_default']:
        # 4.1 如果将当前模型设置为默认，将其他模型的is_default设置为False
        db.query(Model).filter(
            Model.supplier_id == supplier_id,  # 同一供应商
            Model.id != model_id  # 排除当前模型
        ).update({Model.is_default: False})  # 批量更新
    
    # 5. 更新模型字段
    for field, value in update_data.items():
        setattr(model, field, value)  # 使用setattr动态设置模型属性
    
    try:
        # 6. 提交数据库事务
        db.commit()
        
        # 7. 刷新数据库会话以获取最新数据
        db.refresh(model)
        
        # 8. 返回更新后的模型信息
        return model
    except IntegrityError:
        # 9. 处理数据库完整性错误
        db.rollback()  # 回滚事务
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新模型失败，请检查输入数据的有效性和完整性"
        )


@router.delete("/suppliers/{supplier_id}/models/{model_id}", summary="删除模型", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    supplier_id: int,  # 路径参数：供应商ID
    model_id: int,  # 路径参数：模型ID
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> None:
    """
    删除指定供应商下的模型
    
    功能说明：
    - 删除指定供应商下的特定模型
    - 处理默认模型逻辑：如果删除的是默认模型，自动将第一个可用模型设为默认
    - 删除成功后返回204状态码，无响应体
    - 提供完整的错误处理
    
    参数详解：
    - supplier_id: 供应商ID（路径参数）
    - model_id: 模型ID（路径参数）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - None（204 No Content）
    
    异常处理：
    - 404 Not Found: 如果指定的模型不存在，或不属于指定的供应商
    """
    # 1. 根据供应商ID和模型ID查询模型
    model = db.query(Model).filter(
        Model.id == model_id,  # 匹配模型ID
        Model.supplier_id == supplier_id  # 同时匹配供应商ID，确保资源安全
    ).first()
    
    # 2. 验证模型是否存在
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{model_id}的模型不存在于ID为{supplier_id}的供应商下"
        )
    
    # 3. 记录模型是否为默认模型
    was_default = model.is_default  # 保存当前模型的默认状态
    
    # 4. 删除模型
    db.delete(model)  # 从数据库中删除模型
    
    # 5. 处理默认模型逻辑
    if was_default is True:
        # 5.1 如果删除的是默认模型，查找供应商下的第一个可用模型
        first_model = db.query(Model).filter(
            Model.supplier_id == supplier_id  # 同一供应商
        ).first()
        
        # 5.2 如果存在其他模型，将第一个模型设为默认
        if first_model:
            setattr(first_model, 'is_default', True)  # 设置为默认模型
    
    # 6. 提交数据库事务
    db.commit()


@router.post("/suppliers/{supplier_id}/models/set-default/{model_id}", summary="设置默认模型", response_model=ModelResponse)
async def set_default_model(
    supplier_id: int,  # 路径参数：供应商ID
    model_id: int,  # 路径参数：模型ID
    db: Session = Depends(get_db),  # 数据库会话依赖
    current_user: MockUser = Depends(get_mock_user)  # 当前用户（模拟）
) -> Any:
    """
    设置指定供应商的默认模型
    
    功能说明：
    - 将指定供应商下的特定模型设为默认模型
    - 自动将同一供应商下的其他所有模型设为非默认
    - 设置成功后返回更新后的模型信息
    - 提供完整的错误处理
    
    参数详解：
    - supplier_id: 供应商ID（路径参数）
    - model_id: 模型ID（路径参数）
    - db: 数据库会话对象
    - current_user: 当前操作用户
    
    返回结果：
    - 更新后的ModelResponse对象（已设为默认）
    
    异常处理：
    - 404 Not Found: 如果指定的模型不存在，或不属于指定的供应商
    """
    # 1. 验证模型是否存在且属于指定供应商
    model = db.query(Model).filter(
        Model.id == model_id,  # 匹配模型ID
        Model.supplier_id == supplier_id  # 同时匹配供应商ID，确保资源安全
    ).first()
    
    # 2. 检查模型是否存在
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ID为{model_id}的模型不存在于ID为{supplier_id}的供应商下"
        )
    
    # 3. 将同一供应商下的所有模型设为非默认
    db.query(Model).filter(Model.supplier_id == supplier_id).update({Model.is_default: False})  # 批量更新
    
    # 4. 将指定模型设为默认
    setattr(model, 'is_default', True)  # 设置is_default属性为True
    
    # 5. 提交数据库事务
    db.commit()
    
    # 6. 刷新数据库会话以获取最新数据
    db.refresh(model)
    
    # 7. 返回更新后的模型信息
    return model