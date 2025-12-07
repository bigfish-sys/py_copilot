"""
模型管理相关API接口

此模块提供了完整的模型供应商和模型管理功能，包括：
- 模型供应商的增删改查操作
- 模型的增删改查操作
- 供应商logo上传功能
- 默认模型设置功能
- 数据验证和错误处理

技术栈：
- FastAPI：提供RESTful API接口
- SQLAlchemy：数据库ORM操作
- SQLite：轻量级数据库存储

注意事项：
- 当前使用MockUser替代真实用户认证，便于测试
- 文件上传支持多种图片格式
- 数据库操作包含完整的事务处理
"""
from typing import Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import os
import uuid
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# 导入数据库模型：ModelSupplier用于供应商管理，Model用于模型管理
from app.models.supplier_db import SupplierDB as ModelSupplier, ModelDB as Model
# 获取带时区的当前UTC时间
from datetime import datetime, timezone
def get_now()->datetime:
    """
    获取当前带时区的UTC时间
    
    Returns:
        datetime: 带时区的当前UTC时间
    """
    # 获取当前时间并添加时区信息
    return datetime.now(timezone.utc)  

# 创建直接连接到py_copilot.db的数据库会话
def get_db():
    """
    获取数据库会话
    
    使用SQLAlchemy创建数据库引擎和会话工厂，
    通过yield提供数据库会话，确保会话在请求结束后正确关闭。
    
    Returns:
        Session: SQLAlchemy数据库会话对象
    """
    # 创建SQLite数据库引擎
    engine = create_engine('sqlite:///./py_copilot.db')
    # 创建会话工厂，设置自动提交和自动刷新为False
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # 创建数据库会话
    db = SessionLocal()
    try:
        yield db
    finally:
        # 确保在任何情况下都会关闭数据库会话
        db.close()
# 导入数据验证和响应模型
from app.schemas.model_management import (
    ModelSupplierCreate,    # 供应商创建请求模型
    ModelSupplierUpdate,    # 供应商更新请求模型
    ModelSupplierResponse,  # 供应商响应模型
    ModelCreate,           # 模型创建请求模型
    ModelUpdate,           # 模型更新请求模型
    ModelResponse,         # 模型响应模型
    ModelSupplierListResponse,  # 供应商列表响应模型
    ModelListResponse,          # 模型列表响应模型
    SetDefaultModelRequest      # 设置默认模型请求模型
)

# 创建上传目录
# 使用绝对路径确保文件能正确保存
# 获取当前文件的绝对路径，然后回溯到项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 构建上传目录路径，指向前端的公共logo目录
UPLOAD_DIR = os.path.join(BASE_DIR, "../frontend/public/logos/providers")
UPLOAD_DIR = os.path.normpath(UPLOAD_DIR)  # 规范化路径
os.makedirs(UPLOAD_DIR, exist_ok=True)
# 打印上传目录，用于调试
print(f"文件上传目录: {UPLOAD_DIR}")

# 支持的图片扩展名
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# 模拟用户相关定义已在其他地方声明

def allowed_file(filename: str) -> bool:
    """
    检查文件扩展名是否允许
    
    Args:
        filename: 要检查的文件名
    
    Returns:
        bool: 如果文件扩展名在允许列表中返回True，否则返回False
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

async def save_upload_file(upload_file: UploadFile) -> Optional[str]:
    """
    保存上传的文件并返回文件名
    
    Args:
        upload_file: 上传的文件对象
    
    Returns:
        Optional[str]: 保存成功后返回文件名，失败抛出异常
    
    Raises:
        HTTPException: 
            - 400错误：不支持的文件类型或文件名无效
            - 500错误：文件保存失败
    """
    # 验证文件类型
    if not allowed_file(upload_file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的文件类型，请上传图片文件 (png, jpg, jpeg, gif, webp)"
        )
    
    # 生成唯一文件名
    if not upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空"
        )
    # 检查文件名是否有扩展名
    if '.' not in upload_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名必须包含扩展名"
        )
    # 提取文件扩展名
    file_ext = upload_file.filename.rsplit('.', 1)[1].lower()
    # 使用时间戳生成唯一文件名，避免文件名冲突
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        print(f"尝试保存文件到: {file_path}")  # 添加日志
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await upload_file.read()
            buffer.write(content)
        print(f"文件保存成功: {unique_filename}")  # 添加成功日志
        # 返回文件名
        return unique_filename
    except Exception as e:
        print(f"文件保存失败: {str(e)}")  # 添加错误日志
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}"
        )
# 临时注释掉认证依赖以方便测试
# from app.api.deps import get_current_active_superuser
# from app.models.user import User

# 创建一个模拟用户类用于测试
class MockUser:
    """
    模拟用户类，用于开发和测试环境
    
    Attributes:
        id: 用户ID
        is_active: 用户是否激活
        is_superuser: 用户是否为超级用户
    """
    def __init__(self):
        self.id = 1
        self.is_active = True
        self.is_superuser = True

def get_mock_user() -> MockUser:
    """
    获取模拟用户实例
    
    Returns:
        MockUser: 模拟用户对象，具有超级用户权限
    """
    return MockUser()

# 创建API路由器
router = APIRouter()


# 模型供应商管理相关路由
# 创建新的模型供应商
@router.post("/suppliers")
async def create_model_supplier(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    api_endpoint: Optional[str] = Form(None),
    api_key_required: Optional[bool] = Form(False),
    is_active: bool = Form(True),
    logo: Optional[UploadFile] = File(None),
    category: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    api_docs: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    创建新的模型供应商（支持图片上传）
    
    此API允许创建新的模型供应商记录，支持上传供应商logo图片。
    包含名称唯一性验证和文件类型验证。
    
    Args:
        name: 供应商名称（必填）
        description: 供应商描述（可选）
        api_endpoint: API端点URL（可选）
        api_key_required: 是否需要API密钥（默认False）
        is_active: 是否激活（默认True）
        logo: 供应商logo图片（可选）
        category: 供应商类别（可选）
        website: 供应商官方网站（可选）
        api_docs: API文档链接（可选）
        api_key: API密钥（可选，通常用于测试）
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        dict: 创建的模型供应商详细信息，包含display_name字段
    
    Raises:
        HTTPException:
            - 400错误：供应商名称已存在或数据无效
            - 500错误：服务器内部错误
    """
    try:
        # 检查供应商名称是否已存在（防止重复创建）
        existing_supplier = db.query(ModelSupplier).filter(
            ModelSupplier.name == name
        ).first()
        if existing_supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="供应商名称已存在"
            )
        
        # 处理logo上传（如果提供了logo）
        logo_url = None
        if logo:
            logo_url = await save_upload_file(logo)
        
        # 创建新供应商实例
        now = get_now()
        db_supplier = ModelSupplier(
            name=name,                    # 供应商名称
            description=description,      # 供应商描述
            api_endpoint=api_endpoint,    # API接口地址
            api_key_required=api_key_required,  # 是否需要API密钥
            is_active=is_active,          # 是否激活
            logo=logo_url,                # logo文件路径
            category=category,            # 供应商类别
            website=website,              # 官方网站
            api_docs=api_docs,            # API文档链接
            api_key=api_key,              # API密钥
            created_at=now,               # 创建时间
            updated_at=now                # 更新时间
          )
        
        # 添加到数据库
        db.add(db_supplier)
        # 提交事务
        db.commit()
        # 刷新以获取数据库生成的字段（如ID）
        db.refresh(db_supplier)
        
        # 返回响应 - 使用name作为display_name
        # 构建包含所有供应商信息的响应对象
        return {
            "id": db_supplier.id,                # 供应商ID
            "name": db_supplier.name,            # 供应商名称
            "display_name": db_supplier.name,    # 显示名称（与名称相同）
            "description": db_supplier.description,  # 描述
            "api_endpoint": db_supplier.api_endpoint,  # API端点
            "api_key_required": db_supplier.api_key_required,  # 是否需要API密钥
            "is_active": db_supplier.is_active,  # 是否激活
            "logo": db_supplier.logo,            # Logo文件路径
            "category": db_supplier.category,    # 类别
            "website": db_supplier.website,      # 网站
            "api_docs": db_supplier.api_docs,    # API文档
            "api_key": db_supplier.api_key,      # API密钥
            "created_at": db_supplier.created_at,  # 创建时间
            "updated_at": db_supplier.updated_at   # 更新时间
        }
    except IntegrityError:
        # 数据库完整性错误，回滚事务
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="创建供应商失败，请检查输入数据"
        )


@router.get("/suppliers", response_model=ModelSupplierListResponse)
async def get_model_suppliers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    获取模型供应商列表
    
    此API返回所有模型供应商的列表，支持分页功能。
    结果包含供应商总数和分页后的供应商列表。
    
    Args:
        skip: 跳过的记录数，用于分页（默认0）
        limit: 返回的最大记录数，用于分页（默认100）
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        ModelSupplierListResponse: 包含供应商列表和总数的响应对象
    """
    # 查询所有供应商，包括非激活的
    suppliers = db.query(ModelSupplier).offset(skip).limit(limit).all()
    # 获取供应商总数，用于分页计算
    total = db.query(ModelSupplier).count()
    
    # 为每个供应商添加display_name字段，使用name作为默认值
    suppliers_with_display_name = []
    for supplier in suppliers:
        # 创建一个带有display_name属性的对象
        supplier_dict = {
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
        suppliers_with_display_name.append(supplier_dict)
    
    # 返回格式化的响应
    return ModelSupplierListResponse(
        suppliers=suppliers_with_display_name,
        total=total
    )


@router.get("/suppliers/{supplier_id}", response_model=ModelSupplierResponse)
async def get_model_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    获取指定的模型供应商详情
    
    根据供应商ID获取特定供应商的详细信息。
    如果供应商不存在，则返回404错误。
    
    Args:
        supplier_id: 供应商ID
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        ModelSupplierResponse: 供应商详细信息
    
    Raises:
        HTTPException:
            - 404错误：供应商不存在
    """
    # 查询指定ID的供应商
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    # 如果不存在，返回404错误
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    # 返回供应商信息
    return supplier


@router.put("/suppliers/{supplier_id}")
async def update_model_supplier(
    supplier_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    api_endpoint: Optional[str] = Form(None),
    api_key_required: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    logo: Optional[UploadFile] = File(None),
    existing_logo: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    api_docs: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    更新模型供应商信息（支持图片上传）
    
    此API允许部分更新供应商信息，包括可选的logo图片替换。
    支持名称唯一性验证和多场景的logo处理（新上传、保留现有或保持不变）。
    
    Args:
        supplier_id: 供应商ID
        name: 供应商名称（可选）
        description: 供应商描述（可选）
        api_endpoint: API端点（可选）
        api_key_required: 是否需要API密钥（可选）
        is_active: 是否激活（可选）
        logo: 新上传的logo图片（可选）
        existing_logo: 现有logo路径（可选，用于保留已有logo）
        category: 供应商类别（可选）
        website: 供应商网站（可选）
        api_docs: API文档链接（可选）
        api_key: API密钥（可选）
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        dict: 更新后的供应商信息，包含display_name字段
    
    Raises:
        HTTPException:
            - 404错误：供应商不存在
            - 400错误：名称重复或数据无效
            - 500错误：服务器内部错误
    """
    # 查询要更新的供应商
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    # 如果不存在，返回404错误
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    # 检查名称是否重复（仅当名称被修改时）
    if name and name != supplier.name:
        existing_supplier = db.query(ModelSupplier).filter(
            ModelSupplier.name == name
        ).first()
        if existing_supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="供应商名称已存在"
            )
    
    # 更新字段（仅更新提供的字段）
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
    
    # 处理logo上传的三种场景：
    if logo:
        # 1. 如果提供了新的logo文件，保存并更新
        logo_path = await save_upload_file(logo)
        setattr(supplier, 'logo', logo_path)
        print(f"已更新logo为新上传的文件: {logo_path}")
    elif existing_logo is not None:
        # 2. 如果提供了existing_logo参数，使用该路径
        setattr(supplier, 'logo', existing_logo)
        print(f"保留现有logo: {supplier.logo}")
    # 3. 否则，保持原有logo不变
    
    # 更新时间戳
    setattr(supplier, 'updated_at', get_now())
    
    try:
        # 提交事务
        db.commit()
        # 刷新获取最新数据
        db.refresh(supplier)
        
        # 返回响应 - 使用name作为display_name
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
        # 数据库完整性错误，回滚事务
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新供应商失败，请检查输入数据"
        )


@router.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> None:
    """
    删除模型供应商
    
    此API删除指定的供应商。删除前会检查该供应商是否有相关的模型，
    如果有则不允许删除，防止数据引用错误。
    
    Args:
        supplier_id: 供应商ID
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Raises:
        HTTPException:
            - 404错误：供应商不存在
            - 400错误：供应商包含模型，无法删除
    
    Returns:
        None: 成功删除返回204 No Content
    """
    print(f"删除供应商请求，supplier_id: {supplier_id}")
    # 查询要删除的供应商
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    # 如果不存在，返回404错误
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    # 检查是否有相关模型（防止删除包含模型的供应商）
    # 使用查询方式替代直接访问关系属性，避免关系定义问题
    has_models = db.query(Model).filter(Model.supplier_id == supplier_id).first() is not None
    if has_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法删除包含模型的供应商，请先删除相关模型"
        )
    
    # 删除供应商
    db.delete(supplier)
    # 提交事务
    db.commit()
    # 返回204 No Content（通过装饰器中的status_code参数设置）


# ==================================================
# 模型管理相关路由
# ==================================================
@router.post("/suppliers/{supplier_id}/models", response_model=ModelResponse)
async def create_model(
    supplier_id: int,
    model: ModelCreate,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    为指定供应商创建新模型
    
    此API为特定供应商创建新的模型记录。包含供应商存在性验证，
    并处理默认模型的逻辑：
    - 如果设置为默认模型，会自动将同一供应商的其他模型设为非默认
    - 如果是该供应商的第一个模型，自动设为默认模型
    
    Args:
        supplier_id: 供应商ID
        model: 模型创建数据（包含模型名称、类型、参数等）
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        ModelResponse: 创建的模型详细信息
    
    Raises:
        HTTPException:
            - 404错误：供应商不存在
            - 400错误：数据无效
    """
    # 验证供应商是否存在
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    # 确保supplier_id一致（防止客户端提交的supplier_id与URL参数不一致）
    model_data = model.model_dump()  # 将Pydantic模型转换为字典
    model_data['supplier_id'] = supplier_id  # 强制使用URL中的supplier_id
    
    try:
        # 创建新模型实例
        db_model = Model(**model_data)
        db.add(db_model)
        
        # 默认模型逻辑处理：
        # 1. 如果明确设置为默认模型，将其他模型设为非默认
        if db_model.is_default is True:
            db.query(Model).filter(
                Model.supplier_id == supplier_id,
                Model.id != db_model.id  # 避免更新自身（虽然此时还未生成ID）
            ).update({Model.is_default: False})
        # 2. 如果是该供应商的第一个模型，自动设为默认
        elif db.query(Model).filter(Model.supplier_id == supplier_id).count() == 0:
            setattr(db_model, 'is_default', True)
        
        # 提交事务
        db.commit()
        # 刷新获取最新数据
        db.refresh(db_model)
        return db_model
    except IntegrityError:
        # 数据库完整性错误，回滚事务
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="创建模型失败，请检查输入数据"
        )


@router.get("/suppliers/{supplier_id}/models", response_model=ModelListResponse)
async def get_models(
    supplier_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    获取指定供应商的模型列表
    
    此API返回特定供应商的所有模型，支持分页。
    包含供应商存在性验证，并为每个模型提供默认值（如果字段不存在）。
    
    Args:
        supplier_id: 供应商ID
        skip: 跳过的记录数，用于分页（默认0）
        limit: 返回的最大记录数，用于分页（默认100）
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        ModelListResponse: 包含模型列表和总数的响应对象
    
    Raises:
        HTTPException:
            - 404错误：供应商不存在
    """
    # 验证供应商是否存在
    supplier = db.query(ModelSupplier).filter(ModelSupplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商不存在"
        )
    
    # 查询指定供应商的模型，支持分页
    models = db.query(Model).filter(
        Model.supplier_id == supplier_id
    ).offset(skip).limit(limit).all()
    # 获取该供应商的模型总数
    total = db.query(Model).filter(Model.supplier_id == supplier_id).count()
    
    # 转换模型数据为响应格式，为缺少的字段提供默认值
    model_responses = []
    for model in models:
        # 创建符合ModelResponse结构的字典，使用getattr确保字段存在
        model_data = {
            "id": model.id,  # 模型ID
            "supplier_id": model.supplier_id,  # 所属供应商ID
            "model_id": getattr(model, "model_id", str(model.id)),  # 使用id作为默认model_id
            "name": getattr(model, "name", ""),  # 模型名称
            "description": getattr(model, "description", None),  # 模型描述
            "type": getattr(model, "type", "chat"),  # 默认类型为chat
            "context_window": getattr(model, "context_window", 8000),  # 上下文窗口大小
            "default_temperature": getattr(model, "default_temperature", 0.7),  # 默认温度参数
            "default_max_tokens": getattr(model, "max_tokens", 1000) or getattr(model, "default_max_tokens", 1000),  # 最大token数
            "default_top_p": getattr(model, "default_top_p", 1.0),  # 默认top_p参数
            "default_frequency_penalty": getattr(model, "default_frequency_penalty", 0.0),  # 默认频率惩罚
            "default_presence_penalty": getattr(model, "default_presence_penalty", 0.0),  # 默认存在惩罚
            "custom_params": getattr(model, "custom_params", None),  # 自定义参数
            "is_active": getattr(model, "is_active", True),  # 是否激活
            "is_default": getattr(model, "is_default", False),  # 是否默认模型
            "created_at": getattr(model, "created_at", datetime.now()),  # 创建时间
            "updated_at": getattr(model, "updated_at", None),  # 更新时间
            "categories": []  # 分类列表（默认空）
        }
        model_responses.append(model_data)
    
    # 返回格式化的响应
    return ModelListResponse(
        models=model_responses,
        total=total
    )


@router.get("/suppliers/{supplier_id}/models/{model_id}", response_model=ModelResponse)
async def get_model(
    supplier_id: int,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    获取指定的模型详情
    
    根据供应商ID和模型ID获取特定模型的详细信息。
    同时验证模型是否属于指定的供应商。
    
    Args:
        supplier_id: 供应商ID
        model_id: 模型ID
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        ModelResponse: 模型详细信息
    
    Raises:
        HTTPException:
            - 404错误：模型不存在或不属于该供应商
    """
    # 查询指定的模型，同时验证supplier_id匹配
    model = db.query(Model).filter(
        Model.id == model_id,
        Model.supplier_id == supplier_id
    ).first()
    
    # 如果不存在，返回404错误
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    return model


@router.put("/suppliers/{supplier_id}/models/{model_id}", response_model=ModelResponse)
async def update_model(
    supplier_id: int,
    model_id: int,
    model_update: ModelUpdate,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    更新模型信息
    
    此API允许部分更新模型信息。包含模型存在性验证，
    并处理默认模型的特殊逻辑（当设置为默认时，自动将其他模型设为非默认）。
    
    Args:
        supplier_id: 供应商ID
        model_id: 模型ID
        model_update: 更新数据（Pydantic模型，只包含要更新的字段）
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        ModelResponse: 更新后的模型详细信息
    
    Raises:
        HTTPException:
            - 404错误：模型不存在或不属于该供应商
            - 400错误：数据无效
    """
    # 查询要更新的模型，同时验证supplier_id匹配
    model = db.query(Model).filter(
        Model.id == model_id,
        Model.supplier_id == supplier_id
    ).first()
    
    # 如果不存在，返回404错误
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 获取更新数据，只包含明确设置的字段（排除未设置的字段）
    update_data = model_update.model_dump(exclude_unset=True)
    
    # 默认模型特殊处理：
    # 如果更新了is_default为True，需要将同一供应商的其他模型设为非默认
    if 'is_default' in update_data and update_data['is_default']:
        db.query(Model).filter(
            Model.supplier_id == supplier_id,
            Model.id != model_id  # 排除当前模型
        ).update({Model.is_default: False})
    
    # 更新模型字段
    for field, value in update_data.items():
        setattr(model, field, value)
    
    try:
        # 提交事务
        db.commit()
        # 刷新获取最新数据
        db.refresh(model)
        return model
    except IntegrityError:
        # 数据库完整性错误，回滚事务
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="更新模型失败，请检查输入数据"
        )


@router.delete("/suppliers/{supplier_id}/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    supplier_id: int,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> None:
    """
    删除模型
    
    此API删除指定的模型。如果删除的是默认模型，
    会自动将该供应商的第一个可用模型设为默认模型。
    
    Args:
        supplier_id: 供应商ID
        model_id: 模型ID
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Raises:
        HTTPException:
            - 404错误：模型不存在或不属于该供应商
    
    Returns:
        None: 成功删除返回204 No Content
    """
    # 查询要删除的模型，同时验证supplier_id匹配
    model = db.query(Model).filter(
        Model.id == model_id,
        Model.supplier_id == supplier_id
    ).first()
    
    # 如果不存在，返回404错误
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 记录是否为默认模型（用于后续处理）
    was_default = model.is_default
    
    # 删除模型
    db.delete(model)
    
    # 默认模型处理：
    # 如果删除的是默认模型，自动将该供应商的第一个模型设为默认
    if was_default is True:
        first_model = db.query(Model).filter(
            Model.supplier_id == supplier_id
        ).first()  # 获取第一个剩余模型
        if first_model:
            setattr(first_model, 'is_default', True)  # 设置为新的默认模型
    
    # 提交事务
    db.commit()


@router.post("/suppliers/{supplier_id}/models/set-default/{model_id}", response_model=ModelResponse)
async def set_default_model(
    supplier_id: int,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: MockUser = Depends(get_mock_user)
) -> Any:
    """
    设置指定供应商的默认模型
    
    此API将特定模型设为供应商的默认模型。
    首先将该供应商的所有模型设为非默认，然后将指定模型设为默认。
    
    Args:
        supplier_id: 供应商ID
        model_id: 要设为默认的模型ID
        db: 数据库会话依赖
        current_user: 当前用户（模拟）
    
    Returns:
        ModelResponse: 设置为默认的模型详细信息
    
    Raises:
        HTTPException:
            - 404错误：模型不存在或不属于该供应商
    """
    # 验证模型是否存在且属于指定供应商
    model = db.query(Model).filter(
        Model.id == model_id,
        Model.supplier_id == supplier_id
    ).first()
    
    # 如果不存在，返回404错误
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模型不存在"
        )
    
    # 将该供应商的所有模型设为非默认
    db.query(Model).filter(Model.supplier_id == supplier_id).update({Model.is_default: False})
    
    # 将指定模型设为默认
    setattr(model, 'is_default', True)
    
    # 提交事务
    db.commit()
    # 刷新获取最新数据
    db.refresh(model)
    return model