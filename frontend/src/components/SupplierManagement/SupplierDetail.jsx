import React, { useState } from 'react';
import { supplierApi } from '../../utils/api/supplierApi';
import SupplierModal from './SupplierModal';

const SupplierDetail = ({ selectedSupplier, onSupplierSelect, onSupplierUpdate }) => {
  const [currentSupplier, setCurrentSupplier] = useState(null);
  const [isSupplierModalOpen, setIsSupplierModalOpen] = useState(false);
  const [supplierModalMode, setSupplierModalMode] = useState('edit');
  const [saving, setSaving] = useState(false);

  const handleToggleSupplierStatus = async (supplier) => {
    try {
      const newStatus = !supplier.is_active;
      const confirmMessage = newStatus
        ? `确定要启用供应商 "${supplier.name}" 吗？`
        : `确定要停用供应商 "${supplier.name}" 吗？`;

      if (!window.confirm(confirmMessage)) {
        return;
      }

      const apiUrl = `http://localhost:8000/api/model-management/suppliers/${supplier.id}`;
      console.log(`切换供应商状态: ${apiUrl}, 新状态: ${newStatus}`);

      await supplierApi.updateSupplierStatus(supplier.id, newStatus);

      if (onSupplierUpdate) {
        setTimeout(() => onSupplierUpdate(), 0);
      }

      console.log(`供应商状态已${newStatus ? '启用' : '停用'}: ${supplier.name}`);
    } catch (err) {
      console.error('Failed to toggle supplier status:', err);
    }
  };

  const handleEditSupplier = (supplier) => {
    console.log('SupplierDetail: 处理编辑模式，传入的supplier对象:', supplier);
    console.log('SupplierDetail: 处理编辑模式，supplier.isDomestic:', supplier?.isDomestic);
    
    // 确保传递的supplier对象包含isDomestic属性
    const supplierWithDomestic = {
      ...supplier,
      isDomestic: supplier?.isDomestic !== undefined ? supplier.isDomestic : false
    };
    
    setCurrentSupplier(supplierWithDomestic);
    setSupplierModalMode('edit');
    setIsSupplierModalOpen(true);
  };

  const handleCloseSupplierModal = () => {
    setIsSupplierModalOpen(false);
    setCurrentSupplier(null);
  };

  const handleSaveSupplier = async (apiData, frontendData) => {
    try {
      setSaving(true);
      console.log('🔄 handleSaveSupplier - 开始保存供应商');
      console.log('🔄 handleSaveSupplier - 提交的API数据:', apiData);
      console.log('🔄 handleSaveSupplier - 提交的前端数据:', frontendData);
      console.log('🔄 handleSaveSupplier - 当前模态窗口模式:', supplierModalMode);
      console.log('🔄 handleSaveSupplier - 当前供应商状态:', currentSupplier);

      const isFormData = apiData instanceof FormData;
      console.log('🔄 handleSaveSupplier - 是否为FormData对象:', isFormData);

      // 创建新的数据副本，避免直接修改传入的数据
      let dataToSend;
      if (isFormData) {
        // 对于FormData，创建新的FormData并复制所有键值对
        dataToSend = new FormData();
        // 复制原始FormData中的所有键值对
        if (apiData instanceof FormData) {
          for (const [key, value] of apiData.entries()) {
            dataToSend.append(key, value);
          }
        }
        // 如果有isDomestic信息，添加到FormData中
        if (frontendData.isDomestic !== undefined) {
          dataToSend.append('is_domestic', frontendData.isDomestic ? 'true' : 'false');
        }

        // 添加api_key_env_name
        const supplierKey = currentSupplier ?
          (currentSupplier.key || currentSupplier.name).toUpperCase() :
          (dataToSend.get('name') || '').toUpperCase();
        dataToSend.append('api_key_env_name', `API_KEY_${supplierKey}`);
      } else {
        // 对于普通对象，创建新对象
        dataToSend = {
          ...apiData,
          // 设置默认值
          is_active: apiData.is_active !== undefined ? apiData.is_active : true,
          is_domestic: frontendData.isDomestic !== undefined ? frontendData.isDomestic : (apiData.is_domestic !== undefined ? apiData.is_domestic : false)
        };

        // 使用currentSupplier的key或name作为环境变量名的一部分
        const supplierKey = currentSupplier ?
          (currentSupplier.key || currentSupplier.name).toUpperCase() :
          (dataToSend.name || '').toUpperCase();

        dataToSend.api_key_env_name = `API_KEY_${supplierKey}`;
      }

      console.log('✅ handleSaveSupplier - 准备发送到API的数据:', dataToSend);

      let updatedSupplierData;

      if (supplierModalMode === 'edit' && currentSupplier) {
        console.log('处理编辑模式');
        const supplierId = Number(currentSupplier.id);
        console.log('更新供应商ID:', currentSupplier.id, '转换后的数字ID:', supplierId);

        // 使用supplierApi.update方法
        updatedSupplierData = await supplierApi.update(supplierId, dataToSend);
        console.log('DEBUG: API返回的更新后数据:', updatedSupplierData);
      } else {
        console.log('处理添加模式');
        // 添加模式下，调用create方法
        updatedSupplierData = await supplierApi.create(dataToSend);
      }

      // 映射API返回的数据到前端格式
      console.log('SupplierDetail: 映射API数据前，frontendData.isDomestic:', frontendData?.isDomestic);
      console.log('SupplierDetail: 映射API数据前，updatedSupplierData.is_domestic:', updatedSupplierData?.is_domestic);
      
      const frontendFormat = {
        id: updatedSupplierData.id,
        key: String(updatedSupplierData.id),
        name: updatedSupplierData.name,
        description: updatedSupplierData.description,
        isDomestic: frontendData?.isDomestic !== undefined ? frontendData.isDomestic : updatedSupplierData?.is_domestic || false
      };
      
      console.log('SupplierDetail: 映射后的前端数据格式:', frontendFormat);

      // 立即更新本地currentSupplier状态
      setCurrentSupplier(frontendFormat);

      // 如果更新的是当前选中的供应商，同步更新选中状态
      if (selectedSupplier?.id === updatedSupplierData.id) {
        if (onSupplierSelect) {
          console.log('调用onSupplierSelect更新选中的供应商');
          onSupplierSelect(frontendFormat);
        }
      }

      // 刷新供应商列表
      if (onSupplierUpdate) {
        console.log('调用onSupplierUpdate刷新数据');
        // 使用setTimeout确保UI更新后再刷新
        setTimeout(() => onSupplierUpdate(), 0);
      }

      // 关闭模态窗口
      handleCloseSupplierModal();

    } catch (error) {
      console.error('保存供应商失败:', error);
      const errorMessage = `${supplierModalMode === 'add' ? '添加' : '更新'}供应商失败`;
      throw new Error(errorMessage);
    } finally {
      setSaving(false);
      console.log('🔄 handleSaveSupplier - 保存操作完成');
    }
  };

  const getSupplierLogo = (supplier) => {
    if (!supplier) return '';

    try {
      console.log('DEBUG: 获取供应商logo:', supplier.logo);
      // 如果有logo
      if (supplier.logo) {
        // 检测是否为外部URL
        if (supplier.logo.startsWith('http')) {
          // 使用后端代理端点处理外部URL，避免ORB安全限制
          const proxyUrl = `/api/proxy-image?url=${encodeURIComponent(supplier.logo)}`;
          console.log('使用代理URL:', proxyUrl);
          return proxyUrl;
        } else if (supplier.logo.startsWith('/logos/providers/')) {
          // 如果是/logo/providers/开头的相对路径，直接使用
          return supplier.logo;
        } else {
          // 兼容处理：如果是单独的文件名，添加路径前缀
          return `/logos/providers/${supplier.logo}`;
        }
      }
      // 没有logo时的默认路径
      return '/logos/providers/default.png';
    } catch (error) {
      console.error('获取供应商logo失败:', error);
      return '/logos/providers/default.png';
    }
  };

  const handleDeleteSupplier = async (supplier) => {
    if (!window.confirm(`确定要删除供应商 "${supplier.name}" 吗？删除后将无法恢复。`)) {
      return;
    }

    try {
      // 使用api.supplierApi.delete方法删除供应商，确保使用正确的API端口
      await supplierApi.delete(supplier.id);

      // 刷新供应商列表
      if (onSupplierUpdate) {
        onSupplierUpdate();
      }

      // 取消选中当前供应商
      if (onSupplierSelect) {
        onSupplierSelect(null);
      }

    } catch (err) {
      console.error('Failed to delete supplier:', err);
    }
  };

  // 格式化API密钥显示
  const formatApiKey = (apiKey) => {
    if (!apiKey || typeof apiKey !== 'string') return '';
    if (apiKey.length <= 8) return apiKey;
    return `${apiKey.slice(0, 4)}...${apiKey.slice(-4)}`;
  };

  if (!selectedSupplier) {
    return (
      <div className="no-supplier-selected">
        <p>请从左侧选择一个供应商</p>
      </div>
    );
  }

  return (
    <div className="supplier-detail">
      <div className="supplier-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className="supplier-title" style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
          <img
            className="supplier-logo"
            src={getSupplierLogo(selectedSupplier)}
            alt={`${selectedSupplier.name} Logo`}
            onError={(e) => {
              // 图片加载失败时显示默认占位
              e.target.src = '/logos/providers/default.png';
            }}
            style={{ width: '40px', height: '40px', objectFit: 'contain', marginRight: '10px' }}
          />
          <h2 style={{ margin: 0, fontSize: '18px' }}>{selectedSupplier.name}</h2>
          {selectedSupplier.website && (
            <div className="info-row">
              <a
                href={selectedSupplier.website}
                target="_blank"
                rel="noopener noreferrer"
                className="external-link"
                style={{ marginLeft: '10px' }}
              >
                官网
              </a>
            </div>
          )}

          <button
            className="btn-edit"
            onClick={() => handleEditSupplier(selectedSupplier)}
            title="编辑供应商信息"
            style={{
              marginRight: '10px',
              padding: '6px 6px',
              border: '1px solid #969a96ff',
              borderRadius: '4px',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              fontSize: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            ✏️
          </button>
          <button
            className="btn-delete"
            onClick={() => handleDeleteSupplier(selectedSupplier)}
            title="删除供应商"
            style={{
              padding: '6px 6px',
              border: '1px solid #969a96ff',
              borderRadius: '4px',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              fontSize: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            🗑️
          </button>
        </div>
        <div className="supplier-actions" style={{ display: 'flex', alignItems: 'center' }}>
          <label className="toggle-switch" title={selectedSupplier.is_active ? '当前已启用，点击停用' : '当前已停用，点击启用'} style={{
            position: 'relative',
            display: 'inline-block',
            width: '60px',
            height: '34px',
            marginLeft: '20px',
            cursor: 'pointer'
          }}>
            <input
              type="checkbox"
              checked={selectedSupplier.is_active}
              onChange={(e) => {
                const newStatus = !selectedSupplier.is_active;
                const confirmMessage = newStatus
                  ? `确定要启用供应商 "${selectedSupplier.name}" 吗？`
                  : `确定要停用供应商 "${selectedSupplier.name}" 吗？`;

                if (window.confirm(confirmMessage)) {
                  supplierApi.updateSupplierStatus(selectedSupplier.id, newStatus)
                    .then(() => {
                      if (onSupplierUpdate) {
                        setTimeout(() => onSupplierUpdate(), 0);
                      }
                      console.log(`供应商状态已${newStatus ? '启用' : '停用'}: ${selectedSupplier.name}`);
                    })
                    .catch(err => {
                      console.error('Failed to toggle supplier status:', err);
                    });
                }
              }}
              style={{
                opacity: 0,
                width: 0,
                height: 0
              }}
            />
            <span style={{
              position: 'absolute',
              cursor: 'pointer',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: selectedSupplier.is_active ? '#4CAF50' : '#ccc',
              transition: '.4s',
              borderRadius: '34px'
            }}>
            </span>
            <span style={{
              position: 'absolute',
              content: '',
              height: '26px',
              width: '26px',
              left: '4px',
              bottom: '4px',
              backgroundColor: 'white',
              transition: '.4s',
              borderRadius: '50%',
              transform: selectedSupplier.is_active ? 'translateX(26px)' : 'translateX(0)'
            }}>
            </span>
          </label>
        </div>
      </div>
      <div style={{ marginLeft: '10px' }}>   {selectedSupplier.description || '未提供描述'}</div>
      <div className="supplier-info-panel panel">
        <div className="supplier-info-grid">
          <div className="info-row">
            <span className="info-label">API地址:</span>
            <input
              type="url"
              className="info-value"
              value={selectedSupplier.apiUrl || selectedSupplier.api_endpoint || '未设置'}
              readOnly
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                backgroundColor: '#f9f9f9',
                fontFamily: 'inherit'
              }}
            />
            {(selectedSupplier.apiUrl || selectedSupplier.api_endpoint) && (
              <a
                href={selectedSupplier.apiUrl || selectedSupplier.api_endpoint}
                target="_blank"
                rel="noopener noreferrer"
                className="external-link"
                style={{ marginLeft: '10px' }}
              >
                访问
              </a>
            )}
          </div>

          <div className="info-row">
            <span className="info-label">API密钥:</span>
            <input
              type="text"
              className="info-value api-key"
              value={formatApiKey(selectedSupplier.api_key)}
              readOnly
              style={{
                flex: 1,
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                backgroundColor: '#f9f9f9',
                fontFamily: 'inherit'
              }}
            />
            {selectedSupplier.api_key && (
              <button
                className="btn-copy"
                onClick={() => navigator.clipboard.writeText(selectedSupplier.api_key)}
                title="复制API密钥"
                style={{ marginLeft: '10px' }}
              >
                复制
              </button>
            )}
          </div>

          {selectedSupplier.api_docs && (
            <div className="info-row">
              <span className="info-label">查看 {selectedSupplier.name} 的</span>
              <a
                href={selectedSupplier.api_docs}
                target="_blank"
                rel="noopener noreferrer"
                className="external-link"
                style={{ marginLeft: '10px' }}
              >
                API文档
              </a>，以获得更多信息
            </div>
          )}
        </div>
      </div>

      <SupplierModal
        isOpen={isSupplierModalOpen}
        onClose={handleCloseSupplierModal}
        onSave={handleSaveSupplier}
        supplier={currentSupplier}
        mode={supplierModalMode}
      />
    </div>
  );
};

export default SupplierDetail;