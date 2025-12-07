"""模型管理相关的数据校验模型"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.model_category import ModelCategoryResponse


# ModelSupplier 相关schemas
class ModelSupplierBase(BaseModel):
    """模型供应商基础模型
    
    该模型定义了模型供应商的基本字段，作为创建、更新和响应模型的基础类。
    """
    # 配置Pydantic模型，允许使用以"model_"开头的字段名
    model_config = ConfigDict(protected_namespaces=())
    # 供应商名称，必填字段，长度1-100个字符
    name: str = Field(..., min_length=1, max_length=100)
    # 供应商显示名称，必填字段，长度1-100个字符
    display_name: str = Field(..., min_length=1, max_length=100)
    # 供应商描述，可选字段
    description: Optional[str] = None
    # 供应商API基础URL，可选字段
    base_url: Optional[str] = None
    # API密钥环境变量名称，可选字段，用于从环境变量中读取密钥
    api_key_env_name: Optional[str] = None
    # 供应商是否激活，默认为True
    is_active: bool = True
    # 供应商logo图片路径，可选字段
    logo: Optional[str] = None


class ModelSupplierCreate(ModelSupplierBase):
    """创建模型供应商请求模型"""
    pass


class ModelSupplierUpdate(BaseModel):
    """更新模型供应商请求模型"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    base_url: Optional[str] = None
    api_key_env_name: Optional[str] = None
    is_active: Optional[bool] = None


class ModelSupplierResponse(ModelSupplierBase):
    """模型供应商响应模型"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    logo: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# Model 相关schemas
class ModelBase(BaseModel):
    """模型基础模型"""
    model_config = ConfigDict(protected_namespaces=())
    model_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    type: str = Field(..., pattern="^(chat|completion|embedding)$")
    context_window: int = Field(default=8000, ge=1)
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=1000, ge=1)
    default_top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    default_frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    default_presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    custom_params: Optional[Dict[str, Any]] = None
    is_active: bool = True
    is_default: bool = False


class ModelCreate(ModelBase):
    """创建模型请求模型"""
    supplier_id: int


class ModelUpdate(BaseModel):
    """更新模型请求模型"""
    model_id: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    type: Optional[str] = Field(None, pattern="^(chat|completion|embedding)$")
    context_window: Optional[int] = Field(None, ge=1)
    default_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    default_max_tokens: Optional[int] = Field(None, ge=1)
    default_top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    default_frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    default_presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    custom_params: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ModelResponse(ModelBase):
    """模型响应模型"""
    id: int
    supplier_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # 添加分类信息
    categories: List[ModelCategoryResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class ModelWithSupplierResponse(ModelResponse):
    """包含供应商信息的模型响应模型"""
    supplier: ModelSupplierResponse


# 列表响应模型
class ModelSupplierListResponse(BaseModel):
    """模型供应商列表响应模型"""
    suppliers: List[ModelSupplierResponse]
    total: int


class ModelListResponse(BaseModel):
    """模型列表响应模型"""
    models: List[ModelResponse]
    total: int


# 设置默认模型请求
class SetDefaultModelRequest(BaseModel):
    """设置默认模型请求模型"""
    model_id: int